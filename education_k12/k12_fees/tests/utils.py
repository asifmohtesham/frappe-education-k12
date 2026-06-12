import frappe

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


def ensure_company(name="Test K12 School", abbr="TKS", currency="AED"):
    if frappe.db.exists("Company", name):
        return name
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
    if existing:
        return existing
    structure = frappe.get_doc(
        {
            "doctype": "Fee Structure",
            "program": program,
            "academic_year": academic_year,
            "company": company,
            "receivable_account": receivable_account(company),
            "cost_center": cost_center(company),
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
