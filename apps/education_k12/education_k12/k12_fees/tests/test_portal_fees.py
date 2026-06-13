import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.api import fees as fees_api
from education_k12.k12_fees.gateways.mock import MockGateway
from education_k12.k12_fees.tests.utils import make_fees
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.test_portal_api import (
    ensure_guardian,
    ensure_user,
    link_guardian_to_student,
)
from education_k12.k12_sis.tests.utils import ensure_student


class TestPortalFees(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _setup_family(self, tag):
        child = ensure_student(f"Fee Portal Kid {tag}")
        user = ensure_user(
            f"fee.parent.{tag}@test.k12.local", f"Fee Parent {tag}", roles=("Guardian",)
        )
        link_guardian_to_student(child, ensure_guardian(f"Fee Parent {tag}", user))
        fees = make_fees(child)
        fees.insert(ignore_permissions=True)
        fees.submit()
        return child, user, fees

    def test_guardian_sees_own_child_fees(self):
        child, user, fees = self._setup_family("A")
        frappe.set_user(user)
        rows = fees_api.get_child_fees(child)
        names = [r["name"] for r in rows]
        self.assertIn(fees.name, names)
        row = next(r for r in rows if r["name"] == fees.name)
        self.assertEqual(row["outstanding_amount"], fees.grand_total)
        self.assertTrue(row["components"])

    def test_cross_family_fees_rejected(self):
        child_b, _, _ = self._setup_family("B")
        _, user_c, _ = self._setup_family("C")
        frappe.set_user(user_c)
        with self.assertRaises(frappe.PermissionError):
            fees_api.get_child_fees(child_b)
        with self.assertRaises(frappe.PermissionError):
            fees_api.initiate_fee_payment(
                frappe.db.get_value("Fees", {"student": child_b}, "name")
            )

    def test_initiate_payment_returns_mock_url(self):
        child, user, fees = self._setup_family("D")
        frappe.db.set_single_value("K12 Settings", "payment_gateway", "Mock")
        frappe.set_user(user)
        result = fees_api.initiate_fee_payment(fees.name)
        self.assertIn("complete_mock_payment", result["payment_url"])

    def test_mock_payment_completion_clears_outstanding(self):
        child, user, fees = self._setup_family("E")
        frappe.db.set_single_value("K12 Settings", "payment_gateway", "Mock")
        frappe.set_user(user)
        url = fees_api.initiate_fee_payment(fees.name)["payment_url"]
        token = url.split("token=")[1]
        frappe.set_user("Administrator")
        fees_api._complete_mock_payment_for_tests(token)
        fees.reload()
        self.assertEqual(fees.outstanding_amount, 0)
