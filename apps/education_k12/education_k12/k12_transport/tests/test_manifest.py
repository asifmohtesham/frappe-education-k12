import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student
from education_k12.k12_transport.manifest import get_route_manifest
from education_k12.k12_transport.tests.utils import (
    ensure_route,
    ensure_staff,
    ensure_vehicle,
)


class TestRouteManifest(FrappeTestCase):
    def setUp(self):
        self.year = ensure_academic_year()
        driver = ensure_staff("Manifest Driver", "Driver")
        vehicle = ensure_vehicle("DXB M 30001", capacity=10, driver=driver)
        self.route = ensure_route(
            "Route Manifest",
            vehicle,
            stops=[("Stop A", "07:00:00"), ("Stop B", "07:15:00")],
        )

    def _assign(self, student_name, stop_name):
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": ensure_student(student_name),
                "academic_year": self.year,
                "route": self.route,
                "stop_name": stop_name,
            }
        ).insert(ignore_permissions=True)

    def test_manifest_groups_students_by_stop_in_sequence(self):
        self._assign("Manifest Kid B", "Stop B")
        self._assign("Manifest Kid A", "Stop A")
        manifest = get_route_manifest(self.route, self.year)

        self.assertEqual(manifest["route"], self.route)
        self.assertEqual(manifest["vehicle"]["vehicle_number"], "DXB M 30001")
        self.assertEqual(manifest["vehicle"]["driver_name"], "Manifest Driver")
        self.assertEqual([s["stop_name"] for s in manifest["stops"]], ["Stop A", "Stop B"])
        self.assertEqual(len(manifest["stops"][0]["students"]), 1)
        self.assertEqual(len(manifest["stops"][1]["students"]), 1)

    def test_inactive_assignments_excluded(self):
        self._assign("Manifest Kid C", "Stop A")
        assignment = frappe.get_all(
            "K12 Transport Assignment",
            filters={"route": self.route, "academic_year": self.year},
            pluck="name",
        )[0]
        doc = frappe.get_doc("K12 Transport Assignment", assignment)
        doc.active = 0
        doc.save(ignore_permissions=True)

        manifest = get_route_manifest(self.route, self.year)
        total = sum(len(s["students"]) for s in manifest["stops"])
        self.assertEqual(total, 0)

    def test_empty_stops_still_listed(self):
        manifest = get_route_manifest(self.route, self.year)
        self.assertEqual(len(manifest["stops"]), 2)
        self.assertTrue(all(s["students"] == [] for s in manifest["stops"]))
