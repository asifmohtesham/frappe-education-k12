import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.grades import GRADE_LEVELS, create_default_grade_programs


class TestGrades(FrappeTestCase):
    def test_program_has_k12_custom_fields(self):
        meta = frappe.get_meta("Program")
        for fieldname in ("is_k12_grade", "grade_order", "grade_band"):
            self.assertTrue(
                meta.has_field(fieldname), f"Program is missing custom field {fieldname}"
            )

    def test_creates_fourteen_grades_in_order(self):
        create_default_grade_programs()
        grades = frappe.get_all(
            "Program",
            filters={"is_k12_grade": 1},
            fields=["name", "grade_order", "grade_band"],
            order_by="grade_order asc",
        )
        self.assertEqual(len(grades), 14)
        self.assertEqual(grades[0].name, "KG 1")
        self.assertEqual(grades[0].grade_band, "KG")
        self.assertEqual(grades[-1].name, "Grade 12")
        self.assertEqual(grades[-1].grade_band, "Secondary")
        self.assertEqual([g.grade_order for g in grades], list(range(1, 15)))

    def test_seeding_is_idempotent(self):
        create_default_grade_programs()
        second_run_created = create_default_grade_programs()
        self.assertEqual(second_run_created, [])
        self.assertEqual(
            frappe.db.count("Program", {"is_k12_grade": 1}), len(GRADE_LEVELS)
        )
