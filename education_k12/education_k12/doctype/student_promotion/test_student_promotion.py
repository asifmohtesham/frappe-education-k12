import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student

# Prevent Frappe's test runner from loading upstream fixtures for linked
# doctypes (Program Enrollment → Company → Warehouse), which fail in CI
# because ERPNext "Warehouse Type: Transit" is not set up.
test_ignore = [
    "Program Enrollment",
    "Program",
    "Academic Year",
    "Student",
    "Company",
]


def enroll(student, program, year):
    enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student,
            "program": program,
            "academic_year": year,
            "enrollment_date": frappe.utils.today(),
        }
    )
    enrollment.insert(ignore_permissions=True)
    enrollment.submit()
    return enrollment.name


class TestStudentPromotion(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def setUp(self):
        self.year_from = ensure_academic_year("2026-27", "2026-09-01", "2027-06-30")
        self.year_to = ensure_academic_year("2027-28", "2027-09-01", "2028-06-30")

    def make_promotion(self, rows, from_program="Grade 5", to_program="Grade 6"):
        promotion = frappe.get_doc(
            {
                "doctype": "Student Promotion",
                "from_academic_year": self.year_from,
                "to_academic_year": self.year_to,
                "from_program": from_program,
                "to_program": to_program,
            }
        )
        for row in rows:
            promotion.append("students", row)
        return promotion

    def test_same_year_rejected(self):
        promotion = self.make_promotion([])
        promotion.to_academic_year = self.year_from
        with self.assertRaises(frappe.ValidationError):
            promotion.insert(ignore_permissions=True)

    def test_get_students_pulls_enrollments(self):
        s1 = ensure_student("Promo One")
        enroll(s1, "Grade 5", self.year_from)
        promotion = self.make_promotion([])
        promotion.insert(ignore_permissions=True)
        promotion.get_students()
        self.assertIn(s1, [r.student for r in promotion.students])
        self.assertTrue(all(r.action == "Promote" for r in promotion.students))

    def test_submit_creates_target_enrollments(self):
        s_promote = ensure_student("Promo Up")
        s_retain = ensure_student("Promo Stay")
        s_exit = ensure_student("Promo Leave")
        for s in (s_promote, s_retain, s_exit):
            enroll(s, "Grade 5", self.year_from)

        promotion = self.make_promotion(
            [
                {"student": s_promote, "action": "Promote"},
                {"student": s_retain, "action": "Retain"},
                {"student": s_exit, "action": "Exit"},
            ]
        )
        promotion.insert(ignore_permissions=True)
        promotion.submit()

        def enrollment_exists(student, program):
            return frappe.db.exists(
                "Program Enrollment",
                {
                    "student": student,
                    "program": program,
                    "academic_year": self.year_to,
                    "docstatus": 1,
                },
            )

        self.assertTrue(enrollment_exists(s_promote, "Grade 6"))
        self.assertTrue(enrollment_exists(s_retain, "Grade 5"))
        self.assertFalse(enrollment_exists(s_exit, "Grade 5"))
        self.assertFalse(enrollment_exists(s_exit, "Grade 6"))

    def test_submit_skips_existing_enrollment(self):
        s1 = ensure_student("Promo Dup")
        enroll(s1, "Grade 5", self.year_from)
        enroll(s1, "Grade 6", self.year_to)  # already enrolled next year

        promotion = self.make_promotion([{"student": s1, "action": "Promote"}])
        promotion.insert(ignore_permissions=True)
        promotion.submit()  # must not raise / not duplicate

        count = frappe.db.count(
            "Program Enrollment",
            {"student": s1, "program": "Grade 6", "academic_year": self.year_to},
        )
        self.assertEqual(count, 1)
