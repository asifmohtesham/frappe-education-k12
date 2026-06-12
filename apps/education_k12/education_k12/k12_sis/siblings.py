import frappe
from frappe import _


def validate_siblings(doc, method=None):
    for row in doc.siblings:
        if row.student == doc.name:
            frappe.throw(_("A student cannot be their own sibling"))


def sync_reciprocal_siblings(doc, method=None):
    """Ensure every in-school sibling also lists this student back."""
    for row in doc.siblings:
        if not row.student or row.studying_in_same_institute != "YES":
            continue
        sibling = frappe.get_doc("Student", row.student)
        if any(s.student == doc.name for s in sibling.siblings):
            continue
        sibling.append(
            "siblings",
            {
                "student": doc.name,
                "full_name": doc.student_name or doc.first_name,
                "gender": doc.gender,
                "date_of_birth": doc.date_of_birth,
                "studying_in_same_institute": "YES",
            },
        )
        sibling.save(ignore_permissions=True)
