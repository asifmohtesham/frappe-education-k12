import frappe
from frappe.utils import add_days, get_date_str, getdate

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


def ensure_fiscal_year():
    """Ensure a Fiscal Year covering today() exists on the test site.

    ERPNext's Journal Entry (and Fees GL) requires a Fiscal Year that covers
    the posting_date.  Fresh CI sites don't auto-create years, so we seed one
    spanning today's calendar year.
    """
    today = getdate(frappe.utils.today())
    year_str = str(today.year)
    if frappe.db.exists("Fiscal Year", year_str):
        return year_str
    year_start = getdate(f"{today.year}-01-01")
    year_end = getdate(f"{today.year}-12-31")
    try:
        frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": year_str,
                "year_start_date": get_date_str(year_start),
                "year_end_date": get_date_str(year_end),
            }
        ).insert(ignore_permissions=True)
    except frappe.DuplicateEntryError:
        pass
    return year_str


def ensure_company(name="Test K12 School", abbr="TKS", currency="AED"):
    if not frappe.db.exists("Company", name):
        try:
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": name,
                    "abbr": abbr,
                    "default_currency": currency,
                    "country": "United Arab Emirates",
                }
            ).insert(ignore_permissions=True)
        except Exception:
            # On fresh CI sites ERPNext's on_update hook for Company creates default
            # warehouses and requires master data (e.g. "Transit" Warehouse Type)
            # that may not exist yet.  Fall back to the first available company so
            # tests can still run; if none exists, re-raise.
            if not frappe.db.exists("Company", name):
                fallback = frappe.db.get_value("Company", {}, "name")
                if fallback:
                    return fallback
                raise

    # Ensure key company defaults are set so that Fees GL entries succeed.
    # Several Fees fields (income_account, cost_center) are fetch_from fields
    # that chain through Fee Structure → Company defaults.  On fresh CI sites
    # the Company is created without these defaults, leaving the GL entries
    # without required fields (income account needs cost center; JE needs cash
    # account).  We fill them once using the auto-generated Chart of Accounts.
    current = frappe.db.get_value(
        "Company",
        name,
        ["default_income_account", "default_cash_account", "cost_center"],
        as_dict=True,
    ) or {}
    needs_update = {}
    if not current.get("default_income_account"):
        ia = frappe.db.get_value(
            "Account",
            {"company": name, "root_type": "Income", "is_group": 0},
            "name",
        )
        if ia:
            needs_update["default_income_account"] = ia
    if not current.get("default_cash_account"):
        ca = frappe.db.get_value(
            "Account",
            {"company": name, "account_type": "Cash", "is_group": 0},
            "name",
        )
        if ca:
            needs_update["default_cash_account"] = ca
    if not current.get("cost_center"):
        cc = frappe.db.get_value(
            "Cost Center", {"company": name, "is_group": 0}, "name"
        )
        if cc:
            needs_update["cost_center"] = cc
    if needs_update:
        frappe.db.set_value("Company", name, needs_update)

    return name


def receivable_account(company):
    return frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Receivable", "is_group": 0},
        "name",
    )


def income_account(company):
    return frappe.db.get_value(
        "Account",
        {"company": company, "root_type": "Income", "is_group": 0},
        "name",
    )


def cost_center(company):
    return frappe.db.get_value(
        "Cost Center", {"company": company, "is_group": 0}, "name"
    )


def ensure_fee_structure(program, academic_year, company, amount=10000):
    # Look for any fee structure (draft or submitted) — Fees validate does not
    # check fee_structure.docstatus, so a draft is sufficient.
    existing = frappe.db.get_value(
        "Fee Structure",
        {"program": program, "academic_year": academic_year},
    )
    cc = cost_center(company)
    if existing:
        # Patch cost_center if it was created before ensure_company set it.
        if cc and not frappe.db.get_value("Fee Structure", existing, "cost_center"):
            frappe.db.set_value(
                "Fee Structure", existing, "cost_center", cc, update_modified=False
            )
        return existing
    structure = frappe.get_doc(
        {
            "doctype": "Fee Structure",
            "program": program,
            "academic_year": academic_year,
            "company": company,
            "receivable_account": receivable_account(company),
            "cost_center": cc,
            "components": [
                {"fees_category": "Tuition", "amount": amount, "total": amount}
            ],
        }
    )
    structure.insert(ignore_permissions=True)
    # Do not submit — the education app's before_submit hook creates ERPNext
    # Items from Fee Components, which requires a fully-bootstrapped ERPNext
    # instance (Default UOM, item defaults, etc.) that may not be present on
    # fresh test/CI sites.  Fees.validate does not check fee_structure.docstatus.
    return structure.name


def enroll_student(student, program, academic_year):
    existing = frappe.db.get_value(
        "Program Enrollment",
        {"student": student, "program": program, "academic_year": academic_year},
    )
    if existing:
        return existing
    enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student,
            "program": program,
            "academic_year": academic_year,
            "enrollment_date": frappe.utils.today(),
        }
    )
    enrollment.insert(ignore_permissions=True)
    enrollment.submit()
    return enrollment.name


def ensure_fees_submission_prereqs(fees_name, company):
    """Ensure fee_structure and company have non-NULL cost_center and
    income_account before submitting a Fees doc.

    On CI sites the Fee Structure may have been created before the company's
    cost_center / default_income_account were set (e.g. by an earlier test
    class).  Patching the Fee Structure here ensures the fetch_from mechanism
    picks up correct values on the next save (which fees.submit() triggers).
    """
    cc = cost_center(company)
    ia = income_account(company)

    # Patch the Fee Structure so fetch_from chains propagate correctly.
    fee_structure = frappe.db.get_value("Fees", fees_name, "fee_structure")
    if fee_structure:
        fs_row = frappe.db.get_value(
            "Fee Structure", fee_structure, ["cost_center"], as_dict=True
        )
        if fs_row and cc and not fs_row.get("cost_center"):
            frappe.db.set_value(
                "Fee Structure",
                fee_structure,
                "cost_center",
                cc,
                update_modified=False,
            )

    # Also patch the Fees doc directly as a safety net (fetch_from may cache
    # the NULL value in the document row from the initial insert).
    fees_row = frappe.db.get_value(
        "Fees", fees_name, ["cost_center", "income_account"], as_dict=True
    )
    updates = {}
    if cc and not fees_row.get("cost_center"):
        updates["cost_center"] = cc
    if ia and not fees_row.get("income_account"):
        updates["income_account"] = ia
    if updates:
        frappe.db.set_value("Fees", fees_name, updates, update_modified=False)


def make_fees(student, program="Grade 5", academic_year=None, tuition=10000):
    """Build (not insert) a Fees doc wired with company/accounts/enrollment."""
    academic_year = academic_year or ensure_academic_year()
    company = ensure_company()
    return frappe.get_doc(
        {
            "doctype": "Fees",
            "student": student,
            "company": company,
            "academic_year": academic_year,
            "program": program,
            "program_enrollment": enroll_student(student, program, academic_year),
            "fee_structure": ensure_fee_structure(program, academic_year, company),
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.today(),
            "receivable_account": receivable_account(company),
            "income_account": income_account(company),
            "cost_center": cost_center(company),
            "components": [
                {"fees_category": "Tuition", "amount": tuition, "total": tuition}
            ],
        }
    )
