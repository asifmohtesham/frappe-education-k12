import frappe
from frappe import _


def validate_homeroom(doc, method=None):
    if not doc.is_homeroom:
        return
    if not doc.homeroom_teacher:
        frappe.throw(_("A homeroom must have a Homeroom Teacher"))
