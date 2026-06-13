import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.payments import record_fee_payment
from education_k12.k12_fees.tests.utils import (
    ensure_fees_submission_prereqs,
    ensure_fiscal_year,
    make_fees,
)
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_student


class TestRecordFeePayment(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()
        ensure_fiscal_year()  # JE posting_date=today() requires a covering fiscal year

    def _submitted_fees(self, student_name):
        fees = make_fees(ensure_student(student_name))
        fees.insert(ignore_permissions=True)
        # Patch fetch_from fields that may be NULL on CI sites (cost_center,
        # income_account chain through fee_structure → company defaults).
        # We set both in DB (for reload) AND in-memory (for submit's on_submit
        # which reads self.cost_center/income_account directly).
        ensure_fees_submission_prereqs(fees.name, fees.company)
        from education_k12.k12_fees.tests.utils import cost_center, income_account
        company = fees.company
        if not fees.cost_center:
            fees.cost_center = cost_center(company)
        if not fees.income_account:
            fees.income_account = income_account(company)
        fees.submit()
        return fees

    def test_full_payment_clears_outstanding(self):
        fees = self._submitted_fees("Pay Kid Full")
        self.assertEqual(fees.outstanding_amount, fees.grand_total)
        record_fee_payment(fees.name, fees.grand_total, reference="MOCK-1")
        fees.reload()
        self.assertEqual(fees.outstanding_amount, 0)

    def test_partial_payment_reduces_outstanding(self):
        fees = self._submitted_fees("Pay Kid Part")
        record_fee_payment(fees.name, 4000, reference="MOCK-2")
        fees.reload()
        self.assertEqual(fees.outstanding_amount, fees.grand_total - 4000)

    def test_overpayment_rejected(self):
        fees = self._submitted_fees("Pay Kid Over")
        with self.assertRaises(frappe.ValidationError):
            record_fee_payment(fees.name, fees.grand_total + 1, reference="MOCK-3")
