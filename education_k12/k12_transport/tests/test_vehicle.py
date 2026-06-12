import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_transport.tests.utils import ensure_staff


class TestVehicle(FrappeTestCase):
    def test_vehicle_with_driver_and_attendant(self):
        driver = ensure_staff("Driver One", "Driver")
        attendant = ensure_staff("Attendant One", "Attendant")
        vehicle = frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": "DXB A 11111",
                "capacity": 30,
                "driver": driver,
                "attendant": attendant,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(vehicle.name, "DXB A 11111")

    def test_capacity_must_be_positive(self):
        vehicle = frappe.get_doc(
            {"doctype": "K12 Vehicle", "vehicle_number": "DXB A 22222", "capacity": 0}
        )
        with self.assertRaises(frappe.ValidationError):
            vehicle.insert(ignore_permissions=True)

    def test_driver_field_requires_driver_role(self):
        attendant = ensure_staff("Attendant Two", "Attendant")
        vehicle = frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": "DXB A 33333",
                "capacity": 20,
                "driver": attendant,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            vehicle.insert(ignore_permissions=True)
