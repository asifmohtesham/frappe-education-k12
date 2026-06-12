import frappe
from frappe import _
from frappe.model.document import Document


class K12Vehicle(Document):
    def validate(self):
        if (self.capacity or 0) <= 0:
            frappe.throw(_("Seat capacity must be a positive number"))
        self._validate_staff_role("driver", "Driver")
        self._validate_staff_role("attendant", "Attendant")

    def _validate_staff_role(self, fieldname, expected_role):
        staff = self.get(fieldname)
        if not staff:
            return
        role = frappe.db.get_value("K12 Transport Staff", staff, "role")
        if role != expected_role:
            frappe.throw(
                _("{0} must be a transport staff member with role {1}").format(
                    self.meta.get_label(fieldname), expected_role
                )
            )
