import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

K12_ROLES = ("Guardian",)

CUSTOM_FIELDS = {
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
}


def ensure_customizations():
    """Idempotent: runs on install and on every migrate."""
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    ensure_roles()


def ensure_roles():
    for role in K12_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 0}
            ).insert(ignore_permissions=True)
