import frappe
from frappe.tests.utils import FrappeTestCase

GULF_FIELDS = (
    "national_id",
    "national_id_expiry",
    "visa_number",
    "visa_expiry",
    "emergency_contact_name",
    "emergency_contact_phone",
    "medical_conditions",
)


class TestGulfFields(FrappeTestCase):
    def test_student_has_gulf_fields(self):
        meta = frappe.get_meta("Student")
        for fieldname in GULF_FIELDS:
            self.assertTrue(
                meta.has_field(fieldname), f"Student is missing custom field {fieldname}"
            )

    def test_applicant_has_identity_fields(self):
        meta = frappe.get_meta("Student Applicant")
        for fieldname in ("national_id", "national_id_expiry"):
            self.assertTrue(
                meta.has_field(fieldname),
                f"Student Applicant is missing custom field {fieldname}",
            )
