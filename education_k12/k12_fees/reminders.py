"""Daily overdue-fee reminder emails (scheduler)."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, today


def get_due_reminders():
    settings = frappe.get_single("K12 Settings")
    if not settings.enable_fee_reminders:
        return []
    overdue_cutoff = add_days(today(), -(settings.reminder_days_after_due or 0))
    repeat_days = settings.reminder_repeat_days if settings.reminder_repeat_days is not None else 7
    repeat_cutoff = add_days(today(), -repeat_days)
    return frappe.get_all(
        "Fees",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("<=", overdue_cutoff),
        },
        or_filters=[
            ["last_reminder_on", "is", "not set"],
            ["last_reminder_on", "<=", repeat_cutoff],
        ],
        fields=[
            "name",
            "student",
            "student_name",
            "contact_email",
            "outstanding_amount",
            "due_date",
            "currency",
        ],
        order_by="due_date asc",
    )


def send_overdue_fee_reminders():
    sent = []
    for fees in get_due_reminders():
        recipients = _recipients(fees)
        if not recipients:
            continue
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=_("Fee payment reminder — {0}").format(fees.student_name),
                message=_(
                    "Dear parent,<br>Fees {0} for {1} has an outstanding amount of"
                    " {2} {3} (due {4}). Please pay via the parent portal."
                ).format(
                    fees.name,
                    fees.student_name,
                    flt(fees.outstanding_amount),
                    fees.currency or "",
                    fees.due_date,
                ),
            )
        except Exception:
            frappe.log_error(
                title=f"Fee reminder email failed for {fees.name}",
                message=frappe.get_traceback(),
            )
            continue
        frappe.db.set_value(
            "Fees", fees.name, "last_reminder_on", today(), update_modified=False
        )
        sent.append(fees.name)
    return sent


def _recipients(fees):
    if fees.contact_email:
        return [fees.contact_email]
    guardians = frappe.get_all(
        "Student Guardian",
        filters={"parent": fees.student, "parenttype": "Student"},
        pluck="guardian",
    )
    emails = [
        frappe.db.get_value("Guardian", g, "email_address") for g in guardians
    ]
    return [e for e in emails if e]
