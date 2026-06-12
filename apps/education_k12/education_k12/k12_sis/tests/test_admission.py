import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year


def ensure_doc_type(name, mandatory=1):
    if frappe.db.exists("K12 Admission Document Type", name):
        return name
    return (
        frappe.get_doc(
            {
                "doctype": "K12 Admission Document Type",
                "document_name": name,
                "mandatory": mandatory,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_program(name="Test Program"):
    if frappe.db.exists("Program", name):
        return name
    return (
        frappe.get_doc({"doctype": "Program", "program_name": name})
        .insert(ignore_permissions=True)
        .name
    )


def make_applicant(first_name="Applicant One"):
    return frappe.get_doc(
        {
            "doctype": "Student Applicant",
            "first_name": first_name,
            "academic_year": ensure_academic_year(),
            "program": ensure_program(),
        }
    )


class TestAdmissionDocuments(FrappeTestCase):
    def test_new_applicant_gets_mandatory_checklist(self):
        ensure_doc_type("Passport Copy")
        ensure_doc_type("Birth Certificate")
        ensure_doc_type("Optional Photo", mandatory=0)

        applicant = make_applicant()
        applicant.insert(ignore_permissions=True)

        types = [row.document_type for row in applicant.admission_documents]
        self.assertIn("Passport Copy", types)
        self.assertIn("Birth Certificate", types)
        self.assertNotIn("Optional Photo", types)
        self.assertTrue(
            all(row.status == "Pending" for row in applicant.admission_documents)
        )

    def test_existing_checklist_not_overwritten(self):
        ensure_doc_type("Passport Copy")
        applicant = make_applicant("Applicant Two")
        applicant.append(
            "admission_documents",
            {"document_type": "Passport Copy", "status": "Received"},
        )
        applicant.insert(ignore_permissions=True)
        rows = [r for r in applicant.admission_documents if r.document_type == "Passport Copy"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].status, "Received")
