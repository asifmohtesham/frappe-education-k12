import frappe
from frappe import _
from frappe.model.document import Document


class K12TransportRoute(Document):
    def validate(self):
        if not self.stops:
            frappe.throw(_("A route needs at least one stop"))
        seen = set()
        for stop in self.stops:
            if stop.stop_name in seen:
                frappe.throw(_("Duplicate stop: {0}").format(stop.stop_name))
            seen.add(stop.stop_name)
