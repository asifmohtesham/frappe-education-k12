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
        # Patch fee_structure.cost_center and the Fees doc in DB so that when
        # Fees.validate() calls set_missing_accounts_and_fields(), the Company
        # default cost_center and income_account are available.  Then reload
        # from DB so the in-memory document reflects the patched values.
        # We cannot simply set in-memory attributes because fetch_from fires
        # during fees.insert() (is_new=True) and may have overwritten our
        # initial values with NULL fetched from fee_structure.
        ensure_fees_submission_prereqs(fees.name, fees.company)
        fees = frappe.get_doc("Fees", fees.name)  # reload from DB with patched values
        # Diagnostic (CI): log the cost_center after reload so we can confirm
        # the patch is visible before submitting.
        frappe.logger("test_payments").error(
            f"[test_payments] _submitted_fees: fees={fees.name} "
            f"cost_center={fees.cost_center!r} income_account={fees.income_account!r} "
            f"company={fees.company!r} "
            f"Company.cost_center={frappe.db.get_value('Company', fees.company, 'cost_center')!r}"
        )
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
