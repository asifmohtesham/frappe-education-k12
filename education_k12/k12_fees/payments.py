"""Record incoming fee payments against the ERPNext GL."""

import frappe
from frappe import _
from frappe.utils import flt, today


def record_fee_payment(fees_name, amount, reference=None, mode="Online"):
    fees = frappe.get_doc("Fees", fees_name)
    if fees.docstatus != 1:
        frappe.throw(_("Fees {0} is not submitted").format(fees_name))
    amount = flt(amount)
    if amount <= 0:
        frappe.throw(_("Payment amount must be positive"))
    if amount > flt(fees.outstanding_amount):
        frappe.throw(
            _("Payment {0} exceeds outstanding {1}").format(
                amount, fees.outstanding_amount
            )
        )

    journal_entry = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "company": fees.company,
            "posting_date": today(),
            "user_remark": _("Fee payment {0} ({1})").format(
                reference or "", mode
            ).strip(),
            "accounts": [
                {
                    "account": _default_cash_account(fees.company),
                    "debit_in_account_currency": amount,
                },
                {
                    "account": fees.receivable_account,
                    "credit_in_account_currency": amount,
                    "party_type": "Student",
                    "party": fees.student,
                    "reference_type": "Fees",
                    "reference_name": fees.name,
                },
            ],
        }
    )
    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()
    return journal_entry.name


def _default_cash_account(company):
    account = frappe.db.get_value(
        "Company", company, "default_cash_account"
    ) or frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Cash", "is_group": 0},
        "name",
    )
    if not account:
        frappe.throw(_("No cash account found for company {0}").format(company))
    return account
