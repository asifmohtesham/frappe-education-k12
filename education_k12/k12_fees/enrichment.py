"""Per-student Fees enrichment: sibling discount, transport fee, VAT.

Hooked on Fees.before_validate so it runs no matter how the Fees doc is
created (Fee Schedule bulk generation, Desk, API), and BEFORE upstream
calculate_total — upstream remains the single source of totals.

Upstream calculate_total (education v15.2) sums component.amount directly
and ignores the discount field.  Therefore, to make the discount affect
grand_total, this module applies the discount by reducing component.amount
to the post-discount value and stores the percentage in component.discount
for display purposes only.
"""

import frappe
from frappe.utils import flt

OWNED_CATEGORIES = ("Transport", "VAT")


def enrich_fees(doc, method=None):
    _drop_owned_rows(doc)
    _apply_sibling_discount(doc)
    _add_transport_component(doc)
    _add_vat_component(doc)
    _recompute_row_totals(doc)


def _drop_owned_rows(doc):
    doc.components = [
        row for row in doc.components if row.fees_category not in OWNED_CATEGORIES
    ]


def _apply_sibling_discount(doc):
    slabs = sorted(
        frappe.get_single("K12 Settings").sibling_discount_slabs or [],
        key=lambda s: s.sibling_rank,
    )
    if not slabs:
        return
    rank = _sibling_rank(doc.student)
    discount = 0
    for slab in slabs:
        if rank >= slab.sibling_rank:
            discount = slab.discount_percent
    if not discount:
        return
    for row in doc.components:
        if row.fees_category not in OWNED_CATEGORIES:
            original_amount = flt(row.amount)
            row.discount = discount
            # Reduce amount to the discounted value so upstream calculate_total
            # (which sums amount directly) produces the correct grand_total.
            row.amount = flt(original_amount * (1 - discount / 100), 2)


def _sibling_rank(student):
    doc = frappe.get_doc("Student", student)
    members = [(doc.date_of_birth, doc.name)]
    for row in doc.siblings:
        if row.student and row.studying_in_same_institute == "YES":
            dob = frappe.db.get_value("Student", row.student, "date_of_birth")
            members.append((dob, row.student))
    members.sort(key=lambda m: (m[0] is None, m[0] or "", m[1]))
    return [name for _, name in members].index(student) + 1


def _add_transport_component(doc):
    assignment = frappe.get_all(
        "K12 Transport Assignment",
        filters={
            "student": doc.student,
            "academic_year": doc.academic_year,
            "active": 1,
        },
        fields=["route"],
        order_by="creation desc",
        limit=1,
    )
    if not assignment:
        return
    fee = flt(
        frappe.db.get_value(
            "K12 Transport Route", assignment[0].route, "standard_fee"
        )
    )
    if fee <= 0:
        return
    doc.append(
        "components",
        {
            "fees_category": "Transport",
            "amount": fee,
            "description": f"Transport — {assignment[0].route}",
        },
    )


def _add_vat_component(doc):
    rate = flt(frappe.db.get_single_value("K12 Settings", "vat_rate"))
    if rate <= 0:
        return
    taxable_categories = set(
        frappe.get_all("Fee Category", filters={"taxable": 1}, pluck="name")
    )
    base = sum(
        flt(row.amount)
        for row in doc.components
        if row.fees_category in taxable_categories
    )
    if base <= 0:
        return
    doc.append(
        "components",
        {
            "fees_category": "VAT",
            "amount": flt(base * rate / 100, 2),
            "description": f"VAT {flt(rate)}% on taxable items",
        },
    )


def _recompute_row_totals(doc):
    """Set row.total = row.amount (discount already baked into amount)."""
    for row in doc.components:
        row.total = flt(row.amount, 2)
