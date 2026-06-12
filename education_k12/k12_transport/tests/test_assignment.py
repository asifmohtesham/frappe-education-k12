import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student
from education_k12.k12_transport.tests.utils import ensure_route, ensure_vehicle


def assign(student, route, stop_name="Main Gate", **extra):
    return frappe.get_doc(
        {
            "doctype": "K12 Transport Assignment",
            "student": student,
            "academic_year": ensure_academic_year(),
            "route": route,
            "stop_name": stop_name,
            **extra,
        }
    )


class TestTransportAssignment(FrappeTestCase):
    def setUp(self):
        self.route = ensure_route(
            "Route Assign", ensure_vehicle("DXB T 20001", capacity=2)
        )

    def tearDown(self):
        frappe.db.delete(
            "K12 Transport Assignment", {"route": self.route}
        )
        super().tearDown()

    def test_assignment_saves_for_valid_stop(self):
        student = ensure_student("Bus Kid One")
        doc = assign(student, self.route)
        doc.insert(ignore_permissions=True)
        self.assertEqual(
            frappe.db.get_value("K12 Transport Assignment", doc.name, "stop_name"),
            "Main Gate",
        )

    def test_unknown_stop_rejected(self):
        student = ensure_student("Bus Kid Two")
        doc = assign(student, self.route, stop_name="Nowhere")
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_one_active_assignment_per_student_per_year(self):
        student = ensure_student("Bus Kid Three")
        assign(student, self.route).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            assign(student, self.route).insert(ignore_permissions=True)

    def test_inactive_assignment_does_not_block_new_one(self):
        student = ensure_student("Bus Kid Four")
        first = assign(student, self.route)
        first.insert(ignore_permissions=True)
        first.active = 0
        first.save(ignore_permissions=True)
        assign(student, self.route).insert(ignore_permissions=True)  # must not raise

    def test_capacity_enforced(self):
        for index in range(2):  # vehicle capacity is 2
            assign(
                ensure_student(f"Bus Capacity Kid {index}"), self.route
            ).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            assign(ensure_student("Bus Capacity Kid Overflow"), self.route).insert(
                ignore_permissions=True
            )
