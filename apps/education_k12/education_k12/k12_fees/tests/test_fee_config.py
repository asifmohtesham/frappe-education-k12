import frappe
from frappe.tests.utils import FrappeTestCase


class TestFeeConfig(FrappeTestCase):
    def test_k12_settings_has_billing_fields(self):
        meta = frappe.get_meta("K12 Settings")
        for fieldname in (
            "vat_rate",
            "payment_gateway",
            "sibling_discount_slabs",
            "enable_fee_reminders",
            "reminder_days_after_due",
            "reminder_repeat_days",
        ):
            self.assertTrue(
                meta.has_field(fieldname), f"K12 Settings missing {fieldname}"
            )

    def test_fee_category_taxable_flag_and_seeds(self):
        self.assertTrue(frappe.get_meta("Fee Category").has_field("taxable"))
        from education_k12.setup.install import ensure_fee_categories

        ensure_fee_categories()
        self.assertEqual(
            frappe.db.get_value("Fee Category", "Transport", "taxable"), 1
        )
        self.assertEqual(frappe.db.get_value("Fee Category", "Tuition", "taxable"), 0)
        self.assertTrue(frappe.db.exists("Fee Category", "VAT"))

    def test_discount_slab_rows_save(self):
        settings = frappe.get_single("K12 Settings")
        settings.set("sibling_discount_slabs", [])
        settings.append(
            "sibling_discount_slabs", {"sibling_rank": 2, "discount_percent": 10}
        )
        settings.append(
            "sibling_discount_slabs", {"sibling_rank": 3, "discount_percent": 20}
        )
        settings.save()
        saved = frappe.get_single("K12 Settings")
        self.assertEqual(len(saved.sibling_discount_slabs), 2)
