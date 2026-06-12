import frappe
from frappe import _
from frappe.model.document import Document


class K12TransportAssignment(Document):
    def validate(self):
        self.validate_stop_on_route()
        if self.active:
            self.validate_single_active_assignment()
            self.validate_vehicle_capacity()

    def validate_stop_on_route(self):
        stops = frappe.get_all(
            "K12 Route Stop",
            filters={"parent": self.route, "parenttype": "K12 Transport Route"},
            pluck="stop_name",
        )
        if self.stop_name not in stops:
            frappe.throw(
                _("Stop {0} is not on route {1}").format(self.stop_name, self.route)
            )

    def validate_single_active_assignment(self):
        existing = frappe.db.exists(
            "K12 Transport Assignment",
            {
                "student": self.student,
                "academic_year": self.academic_year,
                "active": 1,
                "name": ("!=", self.name),
            },
        )
        if existing:
            frappe.throw(
                _("{0} already has an active transport assignment for {1}").format(
                    self.student_name or self.student, self.academic_year
                )
            )

    def validate_vehicle_capacity(self):
        capacity = frappe.db.get_value(
            "K12 Vehicle",
            frappe.db.get_value("K12 Transport Route", self.route, "vehicle"),
            "capacity",
        )
        occupied = frappe.db.count(
            "K12 Transport Assignment",
            {
                "route": self.route,
                "academic_year": self.academic_year,
                "active": 1,
                "name": ("!=", self.name),
            },
        )
        if occupied >= (capacity or 0):
            frappe.throw(
                _("Route {0} is full ({1} seats)").format(self.route, capacity)
            )
