import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_student


class TestSiblingSync(FrappeTestCase):
    def test_adding_sibling_creates_reciprocal_entry(self):
        a = ensure_student("Sib Alpha")
        b = ensure_student("Sib Beta")

        doc_a = frappe.get_doc("Student", a)
        doc_a.append(
            "siblings",
            {"student": b, "studying_in_same_institute": "YES", "full_name": "Sib Beta"},
        )
        doc_a.save(ignore_permissions=True)

        doc_b = frappe.get_doc("Student", b)
        self.assertIn(a, [row.student for row in doc_b.siblings])

    def test_sync_is_idempotent_on_resave(self):
        a = ensure_student("Sib Gamma")
        b = ensure_student("Sib Delta")
        doc_a = frappe.get_doc("Student", a)
        doc_a.append(
            "siblings",
            {"student": b, "studying_in_same_institute": "YES", "full_name": "Sib Delta"},
        )
        doc_a.save(ignore_permissions=True)
        frappe.get_doc("Student", a).save(ignore_permissions=True)  # resave

        doc_b = frappe.get_doc("Student", b)
        self.assertEqual([row.student for row in doc_b.siblings].count(a), 1)

    def test_student_cannot_be_own_sibling(self):
        a = ensure_student("Sib Self")
        doc_a = frappe.get_doc("Student", a)
        doc_a.append(
            "siblings",
            {"student": a, "studying_in_same_institute": "YES", "full_name": "Sib Self"},
        )
        with self.assertRaises(frappe.ValidationError):
            doc_a.save(ignore_permissions=True)
