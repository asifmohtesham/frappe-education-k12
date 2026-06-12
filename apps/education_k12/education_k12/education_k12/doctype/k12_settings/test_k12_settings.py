import frappe
from frappe.tests.utils import FrappeTestCase


class TestK12Settings(FrappeTestCase):
    def test_singleton_saves_display_name(self):
        settings = frappe.get_single("K12 Settings")
        settings.school_display_name = "Al Noor Test School"
        settings.default_language = "ar"
        settings.save()

        self.assertEqual(
            frappe.db.get_single_value("K12 Settings", "school_display_name"),
            "Al Noor Test School",
        )
        self.assertEqual(
            frappe.db.get_single_value("K12 Settings", "default_language"), "ar"
        )
