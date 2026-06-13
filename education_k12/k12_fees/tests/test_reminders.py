import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from unittest.mock import patch

from education_k12.k12_fees.reminders import get_due_reminders, send_overdue_fee_reminders
from education_k12.k12_fees.tests.utils import make_fees
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_student


class TestFeeReminders(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def _overdue_fees(self, student_name, days_overdue=10, email="p@test.k12.local"):
        fees = make_fees(ensure_student(student_name))
        fees.due_date = add_days(today(), -days_overdue)
        fees.contact_email = email
        fees.insert(ignore_permissions=True)
        fees.submit()
        return fees

    def _settings(self, enabled=1, after=3, repeat=7):
        settings = frappe.get_single("K12 Settings")
        settings.enable_fee_reminders = enabled
        settings.reminder_days_after_due = after
        settings.reminder_repeat_days = repeat
        settings.save()

    def test_overdue_fees_selected(self):
        self._settings()
        fees = self._overdue_fees("Remind Kid One")
        due = get_due_reminders()
        self.assertIn(fees.name, [d.name for d in due])

    def test_recent_or_paid_fees_not_selected(self):
        self._settings(after=30)
        fees = self._overdue_fees("Remind Kid Two", days_overdue=5)
        self.assertNotIn(fees.name, [d.name for d in get_due_reminders()])

    def test_send_marks_last_reminder_and_respects_repeat(self):
        self._settings()
        fees = self._overdue_fees("Remind Kid Three")
        with patch("education_k12.k12_fees.reminders.frappe.sendmail"):
            sent = send_overdue_fee_reminders()
        self.assertIn(fees.name, sent)
        self.assertEqual(
            frappe.db.get_value("Fees", fees.name, "last_reminder_on"),
            frappe.utils.getdate(today()),
        )
        with patch("education_k12.k12_fees.reminders.frappe.sendmail"):
            self.assertEqual(send_overdue_fee_reminders(), [])  # throttled by repeat window

    def test_fee_receipt_print_format_renders(self):
        fees = self._overdue_fees("Remind Kid Print")
        html = frappe.get_print("Fees", fees.name, print_format="K12 Fee Receipt")
        self.assertTrue(html)
        self.assertIn(fees.name, html)
