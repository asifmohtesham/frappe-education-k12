import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

K12_ROLES = ("Guardian",)

CUSTOM_FIELDS = {
    "Student": [
        dict(
            fieldname="k12_identity_section",
            fieldtype="Section Break",
            label="Identity & Visa",
            insert_after="nationality",
        ),
        dict(
            fieldname="national_id",
            fieldtype="Data",
            label="National ID (Emirates ID / Iqama)",
            insert_after="k12_identity_section",
        ),
        dict(
            fieldname="national_id_expiry",
            fieldtype="Date",
            label="National ID Expiry",
            insert_after="national_id",
        ),
        dict(
            fieldname="visa_number",
            fieldtype="Data",
            label="Visa Number",
            insert_after="national_id_expiry",
        ),
        dict(
            fieldname="visa_expiry",
            fieldtype="Date",
            label="Visa Expiry",
            insert_after="visa_number",
        ),
        dict(
            fieldname="k12_welfare_section",
            fieldtype="Section Break",
            label="Emergency & Medical",
            insert_after="visa_expiry",
        ),
        dict(
            fieldname="emergency_contact_name",
            fieldtype="Data",
            label="Emergency Contact Name",
            insert_after="k12_welfare_section",
        ),
        dict(
            fieldname="emergency_contact_phone",
            fieldtype="Data",
            label="Emergency Contact Phone",
            insert_after="emergency_contact_name",
        ),
        dict(
            fieldname="medical_conditions",
            fieldtype="Small Text",
            label="Medical Conditions / Allergies",
            insert_after="emergency_contact_phone",
        ),
    ],
    "Student Applicant": [
        dict(
            fieldname="national_id",
            fieldtype="Data",
            label="National ID (Emirates ID / Iqama)",
            insert_after="nationality",
        ),
        dict(
            fieldname="national_id_expiry",
            fieldtype="Date",
            label="National ID Expiry",
            insert_after="national_id",
        ),
        dict(
            fieldname="k12_documents_section",
            fieldtype="Section Break",
            label="Admission Documents",
            insert_after="application_status",
        ),
        dict(
            fieldname="admission_documents",
            fieldtype="Table",
            options="K12 Admission Document",
            label="Admission Documents",
            insert_after="k12_documents_section",
        ),
    ],
    "Student Group": [
        dict(
            fieldname="is_homeroom",
            fieldtype="Check",
            label="Is Homeroom",
            insert_after="group_based_on",
        ),
        dict(
            fieldname="homeroom_teacher",
            fieldtype="Link",
            options="Instructor",
            label="Homeroom Teacher",
            insert_after="is_homeroom",
            depends_on="is_homeroom",
        ),
    ],
    "Instructor": [
        dict(
            fieldname="user",
            fieldtype="Link",
            options="User",
            label="User",
            insert_after="employee",
            unique=1,
        ),
    ],
    "Program": [
        dict(
            fieldname="k12_grade_section",
            fieldtype="Section Break",
            label="K-12 Grade",
            insert_after="program_abbreviation",
        ),
        dict(
            fieldname="is_k12_grade",
            fieldtype="Check",
            label="Is K-12 Grade",
            insert_after="k12_grade_section",
        ),
        dict(
            fieldname="grade_order",
            fieldtype="Int",
            label="Grade Order",
            insert_after="is_k12_grade",
            depends_on="is_k12_grade",
        ),
        dict(
            fieldname="grade_band",
            fieldtype="Select",
            label="Grade Band",
            options="\nKG\nPrimary\nMiddle\nSecondary",
            insert_after="grade_order",
            depends_on="is_k12_grade",
        ),
    ],
    "Fee Category": [
        dict(
            fieldname="taxable",
            fieldtype="Check",
            label="Taxable (VAT applies)",
            insert_after="description",
        ),
    ],
    "Fees": [
        dict(
            fieldname="last_reminder_on",
            fieldtype="Date",
            label="Last Reminder On",
            read_only=1,
            insert_after="due_date",
        ),
    ],
}


FEE_CATEGORIES = (
    # (category_name, taxable)
    ("Tuition", 0),   # UAE education exemption by default; school-configurable
    ("Transport", 1),
    ("VAT", 0),       # reserved category used for the computed VAT row
)


def ensure_customizations():
    """Idempotent: runs on install and on every migrate."""
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    ensure_roles()
    ensure_fee_categories()


def ensure_roles():
    for role in K12_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 0}
            ).insert(ignore_permissions=True)


def ensure_fee_categories():
    """Seed the standard categories once; never overwrite school edits."""
    for category_name, taxable in FEE_CATEGORIES:
        if not frappe.db.exists("Fee Category", category_name):
            frappe.get_doc(
                {
                    "doctype": "Fee Category",
                    "category_name": category_name,
                    "taxable": taxable,
                }
            ).insert(ignore_permissions=True)
