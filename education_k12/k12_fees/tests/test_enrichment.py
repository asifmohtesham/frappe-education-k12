import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.tests.utils import make_fees
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student
from education_k12.k12_transport.tests.utils import ensure_route, ensure_vehicle


def component_map(fees_doc):
    return {row.fees_category: row for row in fees_doc.components}


def set_slabs(slabs):
    settings = frappe.get_single("K12 Settings")
    settings.set("sibling_discount_slabs", [])
    for rank, pct in slabs:
        settings.append(
            "sibling_discount_slabs", {"sibling_rank": rank, "discount_percent": pct}
        )
    settings.vat_rate = 5
    settings.save()


class TestFeeEnrichment(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def test_vat_added_for_taxable_components_only(self):
        set_slabs([])
        student = ensure_student("Fee Kid VAT")
        fees = make_fees(student)  # Tuition 10000, non-taxable
        fees.insert(ignore_permissions=True)
        comps = component_map(fees)
        self.assertNotIn("VAT", comps)  # nothing taxable yet
        self.assertEqual(fees.grand_total, 10000)

    def test_transport_component_and_vat(self):
        set_slabs([])
        student = ensure_student("Fee Kid Bus")
        academic_year = ensure_academic_year()
        route = ensure_route(
            "Route Fees", ensure_vehicle("DXB F 50001", capacity=10), standard_fee=2000
        )
        if not frappe.db.exists(
            "K12 Transport Assignment",
            {"student": student, "academic_year": academic_year, "active": 1},
        ):
            frappe.get_doc(
                {
                    "doctype": "K12 Transport Assignment",
                    "student": student,
                    "academic_year": academic_year,
                    "route": route,
                    "stop_name": "Main Gate",
                }
            ).insert(ignore_permissions=True)

        fees = make_fees(student)
        fees.insert(ignore_permissions=True)
        comps = component_map(fees)
        self.assertIn("Transport", comps)
        self.assertEqual(comps["Transport"].amount, 2000)
        self.assertIn("VAT", comps)  # transport is taxable: 5% of 2000
        self.assertEqual(comps["VAT"].amount, 100)
        self.assertEqual(fees.grand_total, 12100)

    def test_sibling_discount_applied_by_rank(self):
        set_slabs([(2, 10)])
        elder = ensure_student("Fee Sib Elder", date_of_birth="2014-01-01")
        younger = ensure_student("Fee Sib Younger", date_of_birth="2016-01-01")
        doc = frappe.get_doc("Student", elder)
        doc.append(
            "siblings",
            {
                "student": younger,
                "studying_in_same_institute": "YES",
                "full_name": "Fee Sib Younger",
            },
        )
        doc.save(ignore_permissions=True)

        elder_fees = make_fees(elder)
        elder_fees.insert(ignore_permissions=True)
        self.assertEqual(component_map(elder_fees)["Tuition"].discount, 0)
        self.assertEqual(elder_fees.grand_total, 10000)

        younger_fees = make_fees(younger)
        younger_fees.insert(ignore_permissions=True)
        tuition = component_map(younger_fees)["Tuition"]
        self.assertEqual(tuition.discount, 10)
        self.assertEqual(younger_fees.grand_total, 9000)

    def test_enrichment_idempotent_on_resave(self):
        set_slabs([])
        student = ensure_student("Fee Kid Resave")
        academic_year = ensure_academic_year()
        route = ensure_route(
            "Route Fees R", ensure_vehicle("DXB F 50002", capacity=10), standard_fee=1000
        )
        if not frappe.db.exists(
            "K12 Transport Assignment",
            {"student": student, "academic_year": academic_year, "active": 1},
        ):
            frappe.get_doc(
                {
                    "doctype": "K12 Transport Assignment",
                    "student": student,
                    "academic_year": academic_year,
                    "route": route,
                    "stop_name": "Main Gate",
                }
            ).insert(ignore_permissions=True)
        fees = make_fees(student)
        fees.insert(ignore_permissions=True)
        first_total = fees.grand_total
        fees.save(ignore_permissions=True)  # resave triggers enrichment again
        self.assertEqual(fees.grand_total, first_total)
        self.assertEqual(
            len([c for c in fees.components if c.fees_category == "Transport"]), 1
        )
        self.assertEqual(
            len([c for c in fees.components if c.fees_category == "VAT"]), 1
        )

    def test_no_transport_row_without_assignment(self):
        set_slabs([])
        student = ensure_student("Fee Kid Walks")
        fees = make_fees(student)
        fees.insert(ignore_permissions=True)
        self.assertNotIn("Transport", component_map(fees))

    def test_sibling_discount_stable_across_resaves(self):
        set_slabs([(2, 10)])
        elder = ensure_student("Stable Sib Elder", date_of_birth="2013-01-01")
        younger = ensure_student("Stable Sib Younger", date_of_birth="2015-01-01")
        doc = frappe.get_doc("Student", elder)
        doc.append(
            "siblings",
            {
                "student": younger,
                "studying_in_same_institute": "YES",
                "full_name": "Stable Sib Younger",
            },
        )
        doc.save(ignore_permissions=True)

        fees = make_fees(younger)
        fees.insert(ignore_permissions=True)
        self.assertEqual(fees.grand_total, 9000)

        for _ in range(3):
            fees = frappe.get_doc("Fees", fees.name)
            fees.save(ignore_permissions=True)

        self.assertEqual(fees.grand_total, 9000)
        tuition = next(c for c in fees.components if c.fees_category == "Tuition")
        self.assertEqual(tuition.amount, 9000)
        self.assertEqual(tuition.original_amount, 10000)
        self.assertEqual(tuition.discount, 10)
