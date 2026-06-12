import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_transport.tests.utils import ensure_vehicle


def make_route(route_name, stops):
    doc = frappe.get_doc(
        {
            "doctype": "K12 Transport Route",
            "route_name": route_name,
            "vehicle": ensure_vehicle("DXB R 10001", capacity=40),
        }
    )
    for index, stop_name in enumerate(stops, start=1):
        doc.append("stops", {"stop_name": stop_name, "sequence": index})
    return doc


class TestRoute(FrappeTestCase):
    def test_route_saves_with_ordered_stops_and_fee(self):
        route = make_route("Route Marina", ["Marina Mall", "JBR Walk"])
        route.standard_fee = 1500
        route.insert(ignore_permissions=True)
        saved = frappe.get_doc("K12 Transport Route", "Route Marina")
        self.assertEqual([s.stop_name for s in saved.stops], ["Marina Mall", "JBR Walk"])
        self.assertEqual(saved.standard_fee, 1500)

    def test_route_requires_at_least_one_stop(self):
        route = make_route("Route Empty", [])
        with self.assertRaises(frappe.ValidationError):
            route.insert(ignore_permissions=True)

    def test_duplicate_stop_names_rejected(self):
        route = make_route("Route Dup", ["Same Stop", "Same Stop"])
        with self.assertRaises(frappe.ValidationError):
            route.insert(ignore_permissions=True)
