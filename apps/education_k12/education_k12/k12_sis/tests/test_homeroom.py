import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year


def ensure_instructor(name="Homeroom Teacher One"):
    existing = frappe.db.get_value("Instructor", {"instructor_name": name})
    if existing:
        return existing
    return (
        frappe.get_doc({"doctype": "Instructor", "instructor_name": name})
        .insert(ignore_permissions=True)
        .name
    )


def make_student_group(**overrides):
    year = ensure_academic_year()
    doc = frappe.get_doc(
        {
            "doctype": "Student Group",
            "student_group_name": overrides.pop("student_group_name", "Test Group X"),
            "academic_year": year,
            "group_based_on": "Activity",
            **overrides,
        }
    )
    return doc


class TestHomeroom(FrappeTestCase):
    def test_custom_fields_exist(self):
        sg_meta = frappe.get_meta("Student Group")
        self.assertTrue(sg_meta.has_field("is_homeroom"))
        self.assertTrue(sg_meta.has_field("homeroom_teacher"))
        self.assertTrue(frappe.get_meta("Instructor").has_field("user"))

    def test_homeroom_requires_teacher(self):
        group = make_student_group(
            student_group_name="HR Missing Teacher", is_homeroom=1
        )
        with self.assertRaises(frappe.ValidationError):
            group.insert(ignore_permissions=True)

    def test_valid_homeroom_saves(self):
        group = make_student_group(
            student_group_name="HR 5A",
            is_homeroom=1,
            homeroom_teacher=ensure_instructor(),
        )
        group.insert(ignore_permissions=True)
        self.assertEqual(
            frappe.db.get_value("Student Group", group.name, "is_homeroom"), 1
        )
