# Phase 3 — Fees + Billing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** K-12 fee billing on top of upstream Fees: per-student enrichment (transport fees from Phase 2, sibling discounts, Gulf VAT as a fee component), a pluggable payment-gateway layer (Mock fully working end-to-end; Stripe adapter config-ready), parent portal fee viewing + online payment + receipts, and overdue-fee reminder emails.

**Architecture:** All per-student fee adjustments happen in ONE `before_validate` doc-event on upstream `Fees` so they apply regardless of how the Fees doc is created (Fee Schedule bulk generation or manual). VAT is a Fee Component row — never a side-field — so `grand_total`, GL postings, `outstanding_amount`, and what parents pay always agree. Gateways implement a 2-method interface (`create_checkout`, `handle_callback`) selected via K12 Settings; payments are recorded against Fees through the ERPNext GL so upstream `outstanding_amount` updates natively.

**Tech Stack:** Frappe v15 + ERPNext v15 accounting (Fees GL path), Python 3.11, FrappeTestCase; Vue 3 + frappe-ui.

**Spec:** Phase 3 section of `docs/superpowers/specs/2026-06-12-k12-education-saas-design.md`. SaaS subscription billing of schools stays manual (out of scope). Explicit scope note: real-money gateway verification needs merchant credentials — Mock is the verified end-to-end path; the Stripe adapter is unit-tested against stubbed HTTP and documented as needing keys.

---

## Environment (see README; unchanged)

- Repo (Windows): `C:\Users\asifm\source\repos\frappe-education-k12`; bench (WSL): `~/frappe-bench-dev`, site `dev.localhost`, port 8002. NEVER touch `~/frappe-bench`.
- WSL invoke: `wsl -d Ubuntu -- bash -lc "export PATH=$HOME/.local/bin:$PATH; cd ~/frappe-bench-dev && <cmd>"`. Redis first. Migrate after doctype/custom-field changes.
- Counts today: backend 40, ops 7, frontend 6. Commit trailer: blank line + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## Verified upstream facts (education v15.2 + erpnext v15)

- **Fees** (submittable): `student`+`program_enrollment`+`fee_structure` reqd; `components` (Table Fee Component) reqd; `company` reqd; `receivable_account` reqd; `income_account`, `cost_center`; `grand_total`, `outstanding_amount`; `due_date`+`posting_date` reqd; `contact_email`. `validate` calls `set_missing_accounts_and_fields` + `calculate_total` (sets `grand_total` from components, `outstanding_amount = grand_total`). `on_submit` → `make_gl_entries` (receivable vs income, `update_outstanding="Yes"`); optional ERPNext Payment Request.
- **Fee Component** (child): `fees_category` (Link Fee Category, reqd), `amount` (Currency, reqd), `discount` (Percent), `total` (Float), `description`.
- **Fee Category**: `category_name` reqd, optional ERPNext `item` link.
- **Fee Structure / Fee Schedule**: program-level definitions; Fee Schedule bulk-generates one Fees doc per student. Our per-student logic therefore hooks Fees, not the schedule.
- Payments app (frappe/payments) is NOT installed; we do not depend on it.
- **Critical unknown to verify in T2/T3 (instructions inline):** exactly how upstream `calculate_total` combines `amount`/`discount`/`total`, and which ERPNext voucher type accepts `Fees` as a reference for payments (Journal Entry Account `reference_type` very likely includes `Fees` in this stack since education ships GL integration — verify, fallback documented in T3).

## Design decisions

1. **Single enrichment hook** — `Fees.before_validate` → `k12_fees.enrichment.enrich_fees`: (a) sibling discount onto non-Transport/non-VAT components, (b) transport component from the student's active assignment for the Fees' academic year, (c) VAT component computed over taxable components. Runs before upstream `validate`, so upstream `calculate_total` produces the final totals. Idempotent: rows it owns (Transport, VAT) are deleted and re-added each run.
2. **VAT is a component row** in a reserved Fee Category "VAT" (`taxable=0`). Rate from K12 Settings `vat_rate` (default 5). Which categories attract VAT = `taxable` checkbox custom field on Fee Category (Transport seeded taxable; Tuition seeded non-taxable — UAE education exemption — schools flip per their tax advice).
3. **Sibling discount slabs** live in K12 Settings (child table). Rank = position by date of birth (eldest = 1) among self + in-school siblings. Applicable slab = the one with the largest `sibling_rank` ≤ student's rank.
4. **Gateways**: `k12_fees/gateways/` registry keyed by K12 Settings `payment_gateway` (Select Mock/Stripe). Interface: `create_checkout(fees_doc, success_url) -> dict(payment_url=...)`; `handle_callback(**payload) -> dict(fees=..., amount=..., reference=...)`. Mock is the default and is fully end-to-end (token-protected confirm endpoint). Stripe adapter uses raw `requests` against the Checkout Sessions API + webhook signature verification — no SDK dependency; keys live in `site_config.json` (`stripe_secret_key`, `stripe_webhook_secret`).
5. **Payment recording** — `record_fee_payment(fees, amount, reference)` posts a Journal Entry (debit company default Cash/Bank, credit the Fees' receivable account with `reference_type="Fees"`, `reference_name=<fees>`, party Student) so ERPNext's `update_outstanding` reduces `Fees.outstanding_amount`. T3 verifies `Fees` is an accepted JE reference in this stack and documents the fallback (direct GL Entry pair via `make_gl_entries`, same accounts) if not.
6. **Receipts**: portal endpoint renders the Fees doc to PDF server-side (standard print format) after ownership check; a branded "K12 Fee Receipt" print format ships in T7.
7. **Reminders**: daily scheduler job; one email per overdue Fees per `reminder_repeat_days`; `last_reminder_on` custom field on Fees provides the throttle; global toggle in K12 Settings.

## File map

```
apps/education_k12/education_k12/
├── k12_fees/
│   ├── __init__.py
│   ├── enrichment.py                 # T2 (discount, transport, VAT)
│   ├── payments.py                   # T3 (record_fee_payment)
│   ├── reminders.py                  # T7
│   ├── gateways/ __init__.py (registry), base.py, mock.py, stripe.py   # T3, T4
│   └── tests/ __init__.py, utils.py, test_fee_config.py, test_enrichment.py,
│              test_payments.py, test_gateways.py, test_stripe.py, test_reminders.py
├── api/fees.py                       # T5 portal endpoints (+1 guest-callback endpoint for Stripe webhook in T4)
├── setup/install.py                  # T1 extend (custom fields, fee categories, K12 Settings fields)
├── hooks.py                          # T2 doc_events Fees; T7 scheduler_events
└── education_k12/doctype/k12_sibling_discount_slab/   # T1 child doctype
    └── print_format/k12_fee_receipt/                  # T7

apps/education_k12/frontend/src/
├── pages/parent/ChildFees.vue        # T6
├── pages/parent/ChildProfile.vue     # T6 (link to fees)
├── data/portal.js, router.js, i18n locales  # T6

ops/provision_school.py (+tests)      # T8 (seed fee categories step)
README.md                             # T8
```

Backend test-count math: 40 + T1:3 + T2:5 + T3:4 + T4:3 + T5:4 + T7:3 = **62**; frontend 6 (T6 adds no pure units — verify build/tests only); ops 7 → **8** after T8.

---

### Task 1: Fee configuration foundation

**Files:**
- Create child doctype: `education_k12/doctype/k12_sibling_discount_slab/` (`__init__.py`, json, py)
- Modify: `setup/install.py` (K12 Settings fields via doctype JSON change OR custom fields — see below; Fee Category `taxable` custom field; `ensure_fee_categories`)
- Modify: `education_k12/doctype/k12_settings/k12_settings.json` (new fields — K12 Settings is OUR doctype, edit its JSON directly, no custom fields needed)
- Create: `k12_fees/__init__.py`, `k12_fees/tests/__init__.py` (empty), `k12_fees/tests/test_fee_config.py`

- [ ] **Step 1: failing tests** — `test_fee_config.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase


class TestFeeConfig(FrappeTestCase):
    def test_k12_settings_has_billing_fields(self):
        meta = frappe.get_meta("K12 Settings")
        for fieldname in (
            "vat_rate",
            "payment_gateway",
            "sibling_discount_slabs",
            "enable_fee_reminders",
            "reminder_days_after_due",
            "reminder_repeat_days",
        ):
            self.assertTrue(
                meta.has_field(fieldname), f"K12 Settings missing {fieldname}"
            )

    def test_fee_category_taxable_flag_and_seeds(self):
        self.assertTrue(frappe.get_meta("Fee Category").has_field("taxable"))
        from education_k12.setup.install import ensure_fee_categories

        ensure_fee_categories()
        self.assertEqual(
            frappe.db.get_value("Fee Category", "Transport", "taxable"), 1
        )
        self.assertEqual(frappe.db.get_value("Fee Category", "Tuition", "taxable"), 0)
        self.assertTrue(frappe.db.exists("Fee Category", "VAT"))

    def test_discount_slab_rows_save(self):
        settings = frappe.get_single("K12 Settings")
        settings.set("sibling_discount_slabs", [])
        settings.append(
            "sibling_discount_slabs", {"sibling_rank": 2, "discount_percent": 10}
        )
        settings.append(
            "sibling_discount_slabs", {"sibling_rank": 3, "discount_percent": 20}
        )
        settings.save()
        saved = frappe.get_single("K12 Settings")
        self.assertEqual(len(saved.sibling_discount_slabs), 2)
```

- [ ] **Step 2:** run module `education_k12.k12_fees.tests.test_fee_config` → record failure.

- [ ] **Step 3: implement.**

`k12_sibling_discount_slab.json` (child):

```json
{
 "actions": [],
 "creation": "2026-06-13 09:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["sibling_rank", "discount_percent"],
 "fields": [
  {"fieldname": "sibling_rank", "fieldtype": "Int", "label": "Sibling Rank (2 = second child)", "reqd": 1, "in_list_view": 1},
  {"fieldname": "discount_percent", "fieldtype": "Percent", "label": "Discount %", "reqd": 1, "in_list_view": 1}
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-06-13 09:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Sibling Discount Slab",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

K12 Settings json — append to `field_order` and `fields` (after `default_language`):

```json
  {"fieldname": "billing_section", "fieldtype": "Section Break", "label": "Billing"},
  {"default": "5", "fieldname": "vat_rate", "fieldtype": "Percent", "label": "VAT Rate (%)"},
  {"default": "Mock", "fieldname": "payment_gateway", "fieldtype": "Select", "label": "Payment Gateway", "options": "Mock\nStripe"},
  {"fieldname": "sibling_discount_slabs", "fieldtype": "Table", "label": "Sibling Discount Slabs", "options": "K12 Sibling Discount Slab"},
  {"fieldname": "reminders_section", "fieldtype": "Section Break", "label": "Fee Reminders"},
  {"fieldname": "enable_fee_reminders", "fieldtype": "Check", "label": "Enable Overdue Fee Reminder Emails"},
  {"default": "3", "fieldname": "reminder_days_after_due", "fieldtype": "Int", "label": "Remind After (days past due)"},
  {"default": "7", "fieldname": "reminder_repeat_days", "fieldtype": "Int", "label": "Repeat Every (days)"}
```

`setup/install.py` — add to CUSTOM_FIELDS:

```python
    "Fee Category": [
        dict(
            fieldname="taxable",
            fieldtype="Check",
            label="Taxable (VAT applies)",
            insert_after="description",
        ),
    ],
    "Fees": [
        dict(
            fieldname="last_reminder_on",
            fieldtype="Date",
            label="Last Reminder On",
            read_only=1,
            insert_after="due_date",
        ),
    ],
```

and the seeder + wire it into `ensure_customizations()`:

```python
FEE_CATEGORIES = (
    # (category_name, taxable)
    ("Tuition", 0),   # UAE education exemption by default; school-configurable
    ("Transport", 1),
    ("VAT", 0),       # reserved category used for the computed VAT row
)


def ensure_fee_categories():
    for category_name, taxable in FEE_CATEGORIES:
        if not frappe.db.exists("Fee Category", category_name):
            frappe.get_doc(
                {
                    "doctype": "Fee Category",
                    "category_name": category_name,
                    "taxable": taxable,
                }
            ).insert(ignore_permissions=True)
        else:
            frappe.db.set_value(
                "Fee Category", category_name, "taxable", taxable, update_modified=False
            )
```

(`ensure_customizations` order: create_custom_fields → ensure_roles → ensure_fee_categories — the taxable column must exist before seeding. Re-seeding resets the taxable flag on the three seeded categories only; document in the function docstring that schools customizing these flags should rename/clone categories instead.)

Wait — that reset behavior would override per-school configuration on every migrate. Change: only set `taxable` when CREATING the category; never touch existing ones:

```python
def ensure_fee_categories():
    """Seed the standard categories once; never overwrite school edits."""
    for category_name, taxable in FEE_CATEGORIES:
        if not frappe.db.exists("Fee Category", category_name):
            frappe.get_doc(
                {
                    "doctype": "Fee Category",
                    "category_name": category_name,
                    "taxable": taxable,
                }
            ).insert(ignore_permissions=True)
```

Use this version. The test asserts seeded values on a fresh-seed basis (test site categories are created by this seeder, so the asserted values hold).

- [ ] **Step 4:** migrate; module → 3 OK; full suite → 43 green.
- [ ] **Step 5: Commit** `feat: billing configuration (VAT, gateway, sibling discount slabs, fee categories)`. Push; CI green.

---

### Task 2: Per-student fee enrichment (transport, sibling discount, VAT)

**Files:**
- Create: `k12_fees/enrichment.py`
- Create: `k12_fees/tests/utils.py`
- Test: `k12_fees/tests/test_enrichment.py`
- Modify: `hooks.py` (doc_events Fees before_validate)

**PRE-READ (mandatory):** `~/frappe-bench-dev/apps/education/education/education/doctype/fees/fees.py` — especially `calculate_total` and `set_missing_accounts_and_fields` — and adapt the helper/our row math so upstream totals come out right. The plan's code assumes `calculate_total` sums `component.total` (and that `total` must be set server-side); verify and adjust if it instead derives from `amount`/`discount`.

- [ ] **Step 1: test infrastructure** — `k12_fees/tests/utils.py`:

```python
import frappe

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


def ensure_company(name="Test K12 School", abbr="TKS", currency="AED"):
    if frappe.db.exists("Company", name):
        return name
    frappe.get_doc(
        {
            "doctype": "Company",
            "company_name": name,
            "abbr": abbr,
            "default_currency": currency,
            "country": "United Arab Emirates",
        }
    ).insert(ignore_permissions=True)
    return name


def receivable_account(company):
    return frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Receivable", "is_group": 0},
        "name",
    )


def income_account(company):
    return frappe.db.get_value(
        "Account",
        {"company": company, "root_type": "Income", "is_group": 0},
        "name",
    )


def cost_center(company):
    return frappe.db.get_value(
        "Cost Center", {"company": company, "is_group": 0}, "name"
    )


def ensure_fee_structure(program, academic_year, company, amount=10000):
    existing = frappe.db.get_value(
        "Fee Structure",
        {"program": program, "academic_year": academic_year, "docstatus": 1},
    )
    if existing:
        return existing
    structure = frappe.get_doc(
        {
            "doctype": "Fee Structure",
            "program": program,
            "academic_year": academic_year,
            "company": company,
            "receivable_account": receivable_account(company),
            "cost_center": cost_center(company),
            "components": [
                {"fees_category": "Tuition", "amount": amount, "total": amount}
            ],
        }
    )
    structure.insert(ignore_permissions=True)
    structure.submit()
    return structure.name


def enroll_student(student, program, academic_year):
    existing = frappe.db.get_value(
        "Program Enrollment",
        {"student": student, "program": program, "academic_year": academic_year},
    )
    if existing:
        return existing
    enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student,
            "program": program,
            "academic_year": academic_year,
            "enrollment_date": frappe.utils.today(),
        }
    )
    enrollment.insert(ignore_permissions=True)
    enrollment.submit()
    return enrollment.name


def make_fees(student, program="Grade 5", academic_year=None, tuition=10000):
    """Build (not insert) a Fees doc wired with company/accounts/enrollment."""
    academic_year = academic_year or ensure_academic_year()
    company = ensure_company()
    return frappe.get_doc(
        {
            "doctype": "Fees",
            "student": student,
            "company": company,
            "academic_year": academic_year,
            "program": program,
            "program_enrollment": enroll_student(student, program, academic_year),
            "fee_structure": ensure_fee_structure(program, academic_year, company),
            "posting_date": frappe.utils.today(),
            "due_date": frappe.utils.today(),
            "receivable_account": receivable_account(company),
            "income_account": income_account(company),
            "cost_center": cost_center(company),
            "components": [
                {"fees_category": "Tuition", "amount": tuition, "total": tuition}
            ],
        }
    )
```

(Company creation auto-generates a chart of accounts in ERPNext; if any helper returns None on the dev/CI site, investigate the generated account names rather than hardcoding. If Fee Structure or Fees demands additional mandatory data on this stack — e.g., Education Settings current year — set it in the helper, minimally, and report.)

- [ ] **Step 2: failing tests** — `test_enrichment.py`:

```python
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
        route = ensure_route(
            "Route Fees", ensure_vehicle("DXB F 50001", capacity=10), standard_fee=2000
        )
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": student,
                "academic_year": ensure_academic_year(),
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
        route = ensure_route(
            "Route Fees R", ensure_vehicle("DXB F 50002", capacity=10), standard_fee=1000
        )
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": student,
                "academic_year": ensure_academic_year(),
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
```

- [ ] **Step 3:** run module → record failure (enrichment module missing / components absent).

- [ ] **Step 4: implement** — `k12_fees/enrichment.py`:

```python
"""Per-student Fees enrichment: sibling discount, transport fee, VAT.

Hooked on Fees.before_validate so it runs no matter how the Fees doc is
created (Fee Schedule bulk generation, Desk, API), and BEFORE upstream
calculate_total — upstream remains the single source of totals.
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
        row.discount = discount


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
        _row_total(row)
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


def _row_total(row):
    return flt(row.amount) * (1 - flt(row.discount) / 100)


def _recompute_row_totals(doc):
    for row in doc.components:
        row.total = flt(_row_total(row), 2)
```

(If the PRE-READ shows upstream computes `total` itself or treats `discount` differently, adapt `_recompute_row_totals`/assertions minimally so grand totals match the test expectations — the EXPECTED MONEY VALUES in the tests are the contract; do not change them.)

`hooks.py` doc_events — add:

```python
    "Fees": {
        "before_validate": "education_k12.k12_fees.enrichment.enrich_fees",
    },
```

- [ ] **Step 5:** migrate (custom field last_reminder_on from T1 already in); module → 5 OK; full suite → 48 green.
- [ ] **Step 6: Commit** `feat: per-student fee enrichment (sibling discount, transport, VAT)`. Push; CI green.

---

### Task 3: Gateway interface, Mock gateway, payment recording

**Files:**
- Create: `k12_fees/gateways/__init__.py`, `base.py`, `mock.py`
- Create: `k12_fees/payments.py`
- Tests: `k12_fees/tests/test_payments.py`, `k12_fees/tests/test_gateways.py`

**PRE-READ (mandatory):** check whether `Fees` is an allowed Journal Entry reference: `grep -rn "Fees" ~/frappe-bench-dev/apps/erpnext/erpnext/accounts/doctype/journal_entry_account/journal_entry_account.json` and education's hooks/patches. If JE rejects Fees references, fallback: post the payment GL pair directly via `erpnext.accounts.general_ledger.make_gl_entries` mirroring education's fees.py pattern (against_voucher_type="Fees", update_outstanding="Yes"). Either way the acceptance test is the same: `outstanding_amount` drops.

- [ ] **Step 1: failing tests.**

`test_payments.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.payments import record_fee_payment
from education_k12.k12_fees.tests.utils import make_fees
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_student


class TestRecordFeePayment(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def _submitted_fees(self, student_name):
        fees = make_fees(ensure_student(student_name))
        fees.insert(ignore_permissions=True)
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
```

`test_gateways.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.gateways import get_gateway
from education_k12.k12_fees.gateways.mock import MockGateway, consume_token


class TestGatewayRegistry(FrappeTestCase):
    def test_default_gateway_is_mock(self):
        frappe.db.set_single_value("K12 Settings", "payment_gateway", "Mock")
        self.assertIsInstance(get_gateway(), MockGateway)

    def test_mock_checkout_issues_consumable_token(self):
        gateway = MockGateway()
        result = gateway.create_checkout_for("FEE-TEST-001", 5000)
        self.assertIn("token=", result["payment_url"])
        token = result["payment_url"].split("token=")[1].split("&")[0]
        payload = consume_token(token)
        self.assertEqual(payload["fees"], "FEE-TEST-001")
        self.assertEqual(payload["amount"], 5000)
        self.assertIsNone(consume_token(token))  # single-use
```

- [ ] **Step 2:** run both modules → record failures.

- [ ] **Step 3: implement.**

`gateways/base.py`:

```python
class BaseGateway:
    """Two-method gateway contract.

    create_checkout_for(fees_name, amount) -> {"payment_url": str}
    Callback handling is gateway-specific (token endpoint for Mock,
    signed webhook for Stripe); each gateway converts its callback into a
    record_fee_payment() call.
    """

    def create_checkout_for(self, fees_name, amount):
        raise NotImplementedError
```

`gateways/mock.py`:

```python
"""Development/demo gateway: a single-use token redeemed by a portal endpoint."""

import frappe

from education_k12.k12_fees.gateways.base import BaseGateway

TOKEN_TTL_SECONDS = 3600


def _cache_key(token):
    return f"k12_mock_payment:{token}"


class MockGateway(BaseGateway):
    def create_checkout_for(self, fees_name, amount):
        token = frappe.generate_hash(length=32)
        frappe.cache().set_value(
            _cache_key(token),
            frappe.as_json({"fees": fees_name, "amount": amount}),
            expires_in_sec=TOKEN_TTL_SECONDS,
        )
        return {
            "payment_url": (
                "/api/method/education_k12.api.fees.complete_mock_payment"
                f"?token={token}"
            )
        }


def consume_token(token):
    key = _cache_key(token)
    raw = frappe.cache().get_value(key)
    if not raw:
        return None
    frappe.cache().delete_value(key)
    return frappe.parse_json(raw)
```

`gateways/__init__.py`:

```python
import frappe


def get_gateway():
    from education_k12.k12_fees.gateways.mock import MockGateway

    name = frappe.db.get_single_value("K12 Settings", "payment_gateway") or "Mock"
    if name == "Stripe":
        from education_k12.k12_fees.gateways.stripe import StripeGateway

        return StripeGateway()
    return MockGateway()
```

(Stripe import is lazy so T3 ships before T4 exists — guard: until T4, selecting Stripe raises ImportError; acceptable mid-phase. If you prefer, raise a clear error; either is fine, note what you did.)

`payments.py`:

```python
"""Record incoming fee payments against the ERPNext GL."""

import frappe
from frappe import _
from frappe.utils import flt, today


def record_fee_payment(fees_name, amount, reference=None, mode="Online"):
    fees = frappe.get_doc("Fees", fees_name)
    if fees.docstatus != 1:
        frappe.throw(_("Fees {0} is not submitted").format(fees_name))
    amount = flt(amount)
    if amount <= 0:
        frappe.throw(_("Payment amount must be positive"))
    if amount > flt(fees.outstanding_amount):
        frappe.throw(
            _("Payment {0} exceeds outstanding {1}").format(
                amount, fees.outstanding_amount
            )
        )

    journal_entry = frappe.get_doc(
        {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "company": fees.company,
            "posting_date": today(),
            "user_remark": _("Fee payment {0} ({1})").format(
                reference or "", mode
            ).strip(),
            "accounts": [
                {
                    "account": _default_cash_account(fees.company),
                    "debit_in_account_currency": amount,
                },
                {
                    "account": fees.receivable_account,
                    "credit_in_account_currency": amount,
                    "party_type": "Student",
                    "party": fees.student,
                    "reference_type": "Fees",
                    "reference_name": fees.name,
                },
            ],
        }
    )
    journal_entry.insert(ignore_permissions=True)
    journal_entry.submit()
    return journal_entry.name


def _default_cash_account(company):
    account = frappe.db.get_value(
        "Company", company, "default_cash_account"
    ) or frappe.db.get_value(
        "Account",
        {"company": company, "account_type": "Cash", "is_group": 0},
        "name",
    )
    if not account:
        frappe.throw(_("No cash account found for company {0}").format(company))
    return account
```

(Adapt per the PRE-READ: party_type "Student" on a receivable JE row requires the receivable account's party rules to accept Student — education's GL entries post party Student against that account, so it should. If JE validation rejects `reference_type Fees` or the party, use the direct `make_gl_entries` fallback and keep the same function signature/tests.)

- [ ] **Step 4:** modules → 3 + 3 OK; full suite → 54 green (48 + 6).

Wait — count: T3 adds 3 payments + 3 gateway = 6 tests; the plan summary said T3:4. Use the real numbers: full suite after T3 = **54**; adjust later counts accordingly (T4:+3 → 57; T5:+4 → 61; T7:+3 → 64 final).

- [ ] **Step 5: Commit** `feat: pluggable payment gateways with mock gateway and GL-backed payment recording`. Push; CI green.

---

### Task 4: Stripe adapter (config-driven, stub-tested)

**Files:**
- Create: `k12_fees/gateways/stripe.py`
- Modify: `api/fees.py` placeholder note — webhook endpoint is added in T5 alongside the other endpoints (single commit boundary there); THIS task only ships the adapter + tests.
- Test: `k12_fees/tests/test_stripe.py`

- [ ] **Step 1: failing tests** — `test_stripe.py` (stub `requests` — no network):

```python
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_fees.gateways.stripe import (
    StripeGateway,
    verify_webhook_signature,
)


class TestStripeGateway(FrappeTestCase):
    def setUp(self):
        frappe.conf.stripe_secret_key = "sk_test_dummy"
        frappe.conf.stripe_webhook_secret = "whsec_dummy"

    def test_create_checkout_posts_session(self):
        fake_response = type(
            "Resp",
            (),
            {
                "status_code": 200,
                "json": lambda self: {"url": "https://checkout.stripe.com/pay/cs_test"},
                "text": "",
            },
        )()
        with patch(
            "education_k12.k12_fees.gateways.stripe.requests.post",
            return_value=fake_response,
        ) as post:
            gateway = StripeGateway()
            result = gateway.create_checkout_for("FEE-X-001", 12100)
        self.assertEqual(
            result["payment_url"], "https://checkout.stripe.com/pay/cs_test"
        )
        args, kwargs = post.call_args
        self.assertIn("checkout/sessions", args[0])
        self.assertEqual(kwargs["auth"][0], "sk_test_dummy")
        sent = kwargs["data"]
        self.assertEqual(sent["metadata[fees]"], "FEE-X-001")
        self.assertEqual(sent["line_items[0][price_data][unit_amount]"], 1210000)

    def test_webhook_signature_roundtrip(self):
        payload = json.dumps({"type": "checkout.session.completed"}).encode()
        timestamp = str(int(time.time()))
        signed = hmac.new(
            b"whsec_dummy", f"{timestamp}.".encode() + payload, hashlib.sha256
        ).hexdigest()
        header = f"t={timestamp},v1={signed}"
        self.assertTrue(verify_webhook_signature(payload, header, "whsec_dummy"))

    def test_webhook_bad_signature_rejected(self):
        payload = b"{}"
        header = f"t={int(time.time())},v1=deadbeef"
        self.assertFalse(verify_webhook_signature(payload, header, "whsec_dummy"))
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: implement** — `gateways/stripe.py`:

```python
"""Stripe Checkout adapter (no SDK; raw HTTPS).

Config (site_config.json): stripe_secret_key, stripe_webhook_secret.
Currency: the school site's company currency is assumed Stripe-supported
(AED is). Amounts are sent in fils/cents (x100).

UNVERIFIED AGAINST LIVE STRIPE: unit-tested with stubbed HTTP only. Set
the keys and run a test-mode checkout before offering this to a school.
"""

import hashlib
import hmac
import time

import requests

import frappe
from frappe import _

from education_k12.k12_fees.gateways.base import BaseGateway

API_BASE = "https://api.stripe.com/v1"
SIGNATURE_TOLERANCE_SECONDS = 300


class StripeGateway(BaseGateway):
    def __init__(self):
        self.secret_key = frappe.conf.get("stripe_secret_key")
        if not self.secret_key:
            frappe.throw(_("stripe_secret_key missing from site config"))

    def create_checkout_for(self, fees_name, amount):
        site_url = frappe.utils.get_url()
        currency = (
            frappe.db.get_single_value("Global Defaults", "default_currency") or "AED"
        )
        response = requests.post(
            f"{API_BASE}/checkout/sessions",
            auth=(self.secret_key, ""),
            data={
                "mode": "payment",
                "success_url": f"{site_url}/portal",
                "cancel_url": f"{site_url}/portal",
                "metadata[fees]": fees_name,
                "line_items[0][quantity]": 1,
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][unit_amount]": int(round(amount * 100)),
                "line_items[0][price_data][product_data][name]": f"School fees {fees_name}",
            },
            timeout=30,
        )
        if response.status_code != 200:
            frappe.throw(_("Stripe error: {0}").format(response.text[:300]))
        return {"payment_url": response.json()["url"]}


def verify_webhook_signature(payload, signature_header, webhook_secret):
    try:
        parts = dict(item.split("=", 1) for item in signature_header.split(","))
        timestamp, expected = parts["t"], parts["v1"]
    except (ValueError, KeyError):
        return False
    if abs(time.time() - int(timestamp)) > SIGNATURE_TOLERANCE_SECONDS:
        return False
    computed = hmac.new(
        webhook_secret.encode(),
        f"{timestamp}.".encode() + payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected)
```

- [ ] **Step 4:** module → 3 OK; full suite → 57 green.
- [ ] **Step 5: Commit** `feat: Stripe checkout adapter (config-driven, stub-tested)`. Push; CI green.

---

### Task 5: Portal fee endpoints (view, pay, receipt, callbacks)

**Files:**
- Create: `api/fees.py`
- Test: `k12_fees/tests/test_portal_fees.py`

- [ ] **Step 1: failing tests** — `test_portal_fees.py` (reuses the guardian factories from `k12_sis.tests.test_portal_api` — import them):

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.api import fees as fees_api
from education_k12.k12_fees.gateways.mock import MockGateway
from education_k12.k12_fees.tests.utils import make_fees
from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.test_portal_api import (
    ensure_guardian,
    ensure_user,
    link_guardian_to_student,
)
from education_k12.k12_sis.tests.utils import ensure_student


class TestPortalFees(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        create_default_grade_programs()

    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def _setup_family(self, tag):
        child = ensure_student(f"Fee Portal Kid {tag}")
        user = ensure_user(
            f"fee.parent.{tag}@test.k12.local", f"Fee Parent {tag}", roles=("Guardian",)
        )
        link_guardian_to_student(child, ensure_guardian(f"Fee Parent {tag}", user))
        fees = make_fees(child)
        fees.insert(ignore_permissions=True)
        fees.submit()
        return child, user, fees

    def test_guardian_sees_own_child_fees(self):
        child, user, fees = self._setup_family("A")
        frappe.set_user(user)
        rows = fees_api.get_child_fees(child)
        names = [r["name"] for r in rows]
        self.assertIn(fees.name, names)
        row = next(r for r in rows if r["name"] == fees.name)
        self.assertEqual(row["outstanding_amount"], fees.grand_total)
        self.assertTrue(row["components"])

    def test_cross_family_fees_rejected(self):
        child_b, _, _ = self._setup_family("B")
        _, user_c, _ = self._setup_family("C")
        frappe.set_user(user_c)
        with self.assertRaises(frappe.PermissionError):
            fees_api.get_child_fees(child_b)
        with self.assertRaises(frappe.PermissionError):
            fees_api.initiate_fee_payment(
                frappe.db.get_value("Fees", {"student": child_b}, "name")
            )

    def test_initiate_payment_returns_mock_url(self):
        child, user, fees = self._setup_family("D")
        frappe.db.set_single_value("K12 Settings", "payment_gateway", "Mock")
        frappe.set_user(user)
        result = fees_api.initiate_fee_payment(fees.name)
        self.assertIn("complete_mock_payment", result["payment_url"])

    def test_mock_payment_completion_clears_outstanding(self):
        child, user, fees = self._setup_family("E")
        frappe.set_user(user)
        url = fees_api.initiate_fee_payment(fees.name)["payment_url"]
        token = url.split("token=")[1]
        frappe.set_user("Administrator")
        fees_api._complete_mock_payment_for_tests(token)
        fees.reload()
        self.assertEqual(fees.outstanding_amount, 0)
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: implement** — `api/fees.py`:

```python
"""Parent-portal fee endpoints. Authorization model identical to api/portal.py:
explicit guardian-ownership checks BEFORE any permission-bypassing read."""

import frappe
from frappe import _
from frappe.utils import flt

from education_k12.api.portal import _children_of, _guardian
from education_k12.k12_fees.gateways import get_gateway
from education_k12.k12_fees.gateways.mock import consume_token
from education_k12.k12_fees.gateways.stripe import verify_webhook_signature
from education_k12.k12_fees.payments import record_fee_payment


def _own_student(student):
    guardian = _guardian()
    if student not in _children_of(guardian):
        frappe.throw(_("Not your child"), frappe.PermissionError)


@frappe.whitelist()
def get_child_fees(student):
    _own_student(student)
    rows = frappe.get_all(
        "Fees",
        filters={"student": student, "docstatus": 1},
        fields=[
            "name",
            "due_date",
            "posting_date",
            "grand_total",
            "outstanding_amount",
            "currency",
            "academic_year",
        ],
        order_by="due_date desc",
    )
    for row in rows:
        row["components"] = frappe.get_all(
            "Fee Component",
            filters={"parent": row["name"], "parenttype": "Fees"},
            fields=["fees_category", "amount", "discount", "total", "description"],
            order_by="idx asc",
        )
    return rows


def _own_fees(fees_name):
    fees = frappe.db.get_value(
        "Fees",
        fees_name,
        ["name", "student", "outstanding_amount", "docstatus"],
        as_dict=True,
    )
    if not fees:
        frappe.throw(_("Not your fees"), frappe.PermissionError)
    _own_student(fees.student)
    return fees


@frappe.whitelist()
def initiate_fee_payment(fees_name):
    fees = _own_fees(fees_name)
    if fees.docstatus != 1 or flt(fees.outstanding_amount) <= 0:
        frappe.throw(_("Nothing outstanding on {0}").format(fees_name))
    return get_gateway().create_checkout_for(fees.name, flt(fees.outstanding_amount))


@frappe.whitelist()
def complete_mock_payment(token):
    """Landing endpoint for the Mock gateway's payment_url (logged-in parent)."""
    payload = consume_token(token)
    if not payload:
        frappe.throw(_("Payment link expired or already used"))
    record_fee_payment(
        payload["fees"], payload["amount"], reference=f"MOCK-{token[:8]}", mode="Mock"
    )
    frappe.db.commit()
    frappe.local.response["type"] = "redirect"
    frappe.local.response["location"] = "/portal"


def _complete_mock_payment_for_tests(token):
    """Test seam: same flow without the HTTP redirect plumbing."""
    payload = consume_token(token)
    if not payload:
        frappe.throw(_("Payment link expired or already used"))
    record_fee_payment(
        payload["fees"], payload["amount"], reference=f"MOCK-{token[:8]}", mode="Mock"
    )


@frappe.whitelist(allow_guest=True)
def stripe_webhook():
    """Stripe checkout.session.completed → record payment. Signature-verified."""
    secret = frappe.conf.get("stripe_webhook_secret")
    payload = frappe.request.data
    header = frappe.get_request_header("Stripe-Signature") or ""
    if not secret or not verify_webhook_signature(payload, header, secret):
        frappe.throw(_("Invalid signature"), frappe.PermissionError)
    event = frappe.parse_json(payload)
    if event.get("type") != "checkout.session.completed":
        return "ignored"
    session = event["data"]["object"]
    record_fee_payment(
        session["metadata"]["fees"],
        flt(session["amount_total"]) / 100,
        reference=session.get("payment_intent"),
        mode="Stripe",
    )
    return "ok"


@frappe.whitelist()
def download_receipt(fees_name):
    _own_fees(fees_name)
    html = frappe.get_print("Fees", fees_name, print_format=_receipt_format())
    frappe.local.response.filename = f"{fees_name}-receipt.pdf"
    frappe.local.response.filecontent = frappe.utils.pdf.get_pdf(html)
    frappe.local.response.type = "pdf"


def _receipt_format():
    return (
        "K12 Fee Receipt"
        if frappe.db.exists("Print Format", "K12 Fee Receipt")
        else "Standard"
    )
```

Note `_guardian()` in api/portal.py takes no args in the current code (reads session user internally) — IMPORT-CHECK: read `api/portal.py` first; if `_guardian` has signature `_guardian()` use as-is; the plan's call sites assume that.

- [ ] **Step 4:** module → 4 OK; full suite → 61 green.
- [ ] **Step 5: Commit** `feat: parent portal fee endpoints with mock payment flow and stripe webhook`. Push; CI green.

---

### Task 6: Portal frontend — fees page with pay + receipt

**Files:**
- Create: `frontend/src/pages/parent/ChildFees.vue`
- Modify: `frontend/src/pages/parent/ChildProfile.vue` (link), `frontend/src/data/portal.js`, `frontend/src/router.js`, `i18n/locales/en.json`, `ar.json`

- [ ] **Step 1:** `data/portal.js` — add:

```js
export function childFees(studentId) {
  return createResource({
    url: 'education_k12.api.fees.get_child_fees',
    params: { student: studentId },
    auto: true,
  })
}

export const initiatePayment = createResource({
  url: 'education_k12.api.fees.initiate_fee_payment',
})
```

- [ ] **Step 2:** `pages/parent/ChildFees.vue`:

```vue
<template>
  <div class="p-8">
    <router-link
      class="text-sm text-blue-600"
      :to="{ name: 'ChildProfile', params: { studentId: route.params.studentId } }"
    >
      ← {{ $t('parent.backToProfile') }}
    </router-link>
    <h1 class="mb-4 mt-2 text-2xl font-semibold">{{ $t('parent.fees') }}</h1>
    <div v-if="fees.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!fees.data?.length" class="text-gray-600">
      {{ $t('parent.noFees') }}
    </p>
    <div v-else class="space-y-6">
      <div v-for="bill in fees.data" :key="bill.name" class="rounded-lg border p-4">
        <div class="mb-2 flex items-center justify-between">
          <div>
            <div class="font-medium">{{ bill.name }}</div>
            <div class="text-sm text-gray-600">
              {{ $t('parent.dueDate') }}: {{ bill.due_date }}
            </div>
          </div>
          <div class="text-end">
            <div class="text-lg font-semibold">
              {{ bill.grand_total }} {{ bill.currency }}
            </div>
            <div
              class="text-sm"
              :class="bill.outstanding_amount > 0 ? 'text-orange-600' : 'text-green-600'"
            >
              {{
                bill.outstanding_amount > 0
                  ? $t('parent.outstanding') + ': ' + bill.outstanding_amount
                  : $t('parent.paid')
              }}
            </div>
          </div>
        </div>
        <table class="mb-3 w-full text-sm">
          <tbody>
            <tr v-for="component in bill.components" :key="component.fees_category" class="border-t">
              <td class="py-1">{{ component.fees_category }}</td>
              <td class="py-1 text-end">
                {{ component.total }}
                <span v-if="component.discount" class="text-xs text-gray-500">
                  (-{{ component.discount }}%)
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="flex gap-2">
          <Button
            v-if="bill.outstanding_amount > 0"
            variant="solid"
            :loading="payingBill === bill.name"
            @click="pay(bill.name)"
          >
            {{ $t('parent.payNow') }}
          </Button>
          <a
            v-if="bill.outstanding_amount < bill.grand_total"
            class="text-sm text-blue-600 underline"
            :href="receiptUrl(bill.name)"
            target="_blank"
          >
            {{ $t('parent.downloadReceipt') }}
          </a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { Button } from 'frappe-ui'
import { childFees, initiatePayment } from '../../data/portal'

const route = useRoute()
const fees = childFees(route.params.studentId)
const payingBill = ref(null)

async function pay(billName) {
  payingBill.value = billName
  try {
    const result = await initiatePayment.submit({ fees_name: billName })
    window.location.href = result.payment_url
  } finally {
    payingBill.value = null
  }
}

function receiptUrl(billName) {
  return `/api/method/education_k12.api.fees.download_receipt?fees_name=${encodeURIComponent(billName)}`
}
</script>
```

- [ ] **Step 3:** route + link + i18n.

Router: `{ path: '/children/:studentId/fees', name: 'ChildFees', component: () => import('./pages/parent/ChildFees.vue') }`.

ChildProfile.vue — add under the back-link (a button-styled router-link):

```vue
    <router-link
      class="mt-2 inline-block text-sm text-blue-600 underline"
      :to="{ name: 'ChildFees', params: { studentId: route.params.studentId } }"
    >
      {{ $t('parent.viewFees') }}
    </router-link>
```

en.json parent additions: `"fees": "Fees"`, `"viewFees": "View fees & payments"`, `"backToProfile": "Back to profile"`, `"noFees": "No fee records yet."`, `"dueDate": "Due date"`, `"outstanding": "Outstanding"`, `"paid": "Paid"`, `"payNow": "Pay now"`, `"downloadReceipt": "Download receipt"`.
ar.json: `"fees": "الرسوم"`, `"viewFees": "عرض الرسوم والمدفوعات"`, `"backToProfile": "العودة إلى الملف"`, `"noFees": "لا توجد سجلات رسوم بعد."`, `"dueDate": "تاريخ الاستحقاق"`, `"outstanding": "المتبقي"`, `"paid": "مدفوع"`, `"payNow": "ادفع الآن"`, `"downloadReceipt": "تحميل الإيصال"`.

- [ ] **Step 4:** `npm test` (6) + `npm run build` OK. Live smoke (best effort): bench up, portal serves, `/api/method/education_k12.api.fees.get_child_fees` returns 403 for guest (not 404). Stop bench.
- [ ] **Step 5: Commit** `feat: parent portal fees page with online payment and receipts`. Push; CI green.

---

### Task 7: Overdue reminders + receipt print format

**Files:**
- Create: `k12_fees/reminders.py`
- Create print format: `education_k12/print_format/__init__.py`, `education_k12/print_format/k12_fee_receipt/__init__.py`, `k12_fee_receipt.json`
- Test: `k12_fees/tests/test_reminders.py`
- Modify: `hooks.py` (scheduler_events daily)

- [ ] **Step 1: failing tests** — `test_reminders.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

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
        sent = send_overdue_fee_reminders()
        self.assertIn(fees.name, sent)
        self.assertEqual(
            frappe.db.get_value("Fees", fees.name, "last_reminder_on"), 
            frappe.utils.getdate(today()),
        )
        self.assertEqual(send_overdue_fee_reminders(), [])  # throttled by repeat window
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: implement** — `k12_fees/reminders.py`:

```python
"""Daily overdue-fee reminder emails (scheduler)."""

import frappe
from frappe import _
from frappe.utils import add_days, flt, today


def get_due_reminders():
    settings = frappe.get_single("K12 Settings")
    if not settings.enable_fee_reminders:
        return []
    overdue_cutoff = add_days(today(), -(settings.reminder_days_after_due or 0))
    repeat_cutoff = add_days(today(), -(settings.reminder_repeat_days or 7))
    return frappe.get_all(
        "Fees",
        filters={
            "docstatus": 1,
            "outstanding_amount": (">", 0),
            "due_date": ("<=", overdue_cutoff),
        },
        or_filters=[
            ["last_reminder_on", "is", "not set"],
            ["last_reminder_on", "<=", repeat_cutoff],
        ],
        fields=[
            "name",
            "student",
            "student_name",
            "contact_email",
            "outstanding_amount",
            "due_date",
            "currency",
        ],
    )


def send_overdue_fee_reminders():
    sent = []
    for fees in get_due_reminders():
        recipients = _recipients(fees)
        if not recipients:
            continue
        frappe.sendmail(
            recipients=recipients,
            subject=_("Fee payment reminder — {0}").format(fees.student_name),
            message=_(
                "Dear parent,<br>Fees {0} for {1} has an outstanding amount of"
                " {2} {3} (due {4}). Please pay via the parent portal."
            ).format(
                fees.name,
                fees.student_name,
                flt(fees.outstanding_amount),
                fees.currency or "",
                fees.due_date,
            ),
        )
        frappe.db.set_value(
            "Fees", fees.name, "last_reminder_on", today(), update_modified=False
        )
        sent.append(fees.name)
    return sent


def _recipients(fees):
    if fees.contact_email:
        return [fees.contact_email]
    guardians = frappe.get_all(
        "Student Guardian",
        filters={"parent": fees.student, "parenttype": "Student"},
        pluck="guardian",
    )
    emails = [
        frappe.db.get_value("Guardian", g, "email_address") for g in guardians
    ]
    return [e for e in emails if e]
```

hooks.py:

```python
scheduler_events = {
    "daily": [
        "education_k12.k12_fees.reminders.send_overdue_fee_reminders",
    ],
}
```

Print format `k12_fee_receipt.json` — a standard exported Print Format record for doctype Fees (`"doc_type": "Fees"`, `"print_format_type": "Jinja"`, `"standard": "Yes"`, module Education K12) whose HTML shows: school_display_name from K12 Settings, fees name/dates/student, components table (category, amount, discount, total), grand total, outstanding, and a PAID stamp when outstanding is 0. Keep the HTML simple inline Jinja (`{{ doc.name }}` etc.) — exact markup is the implementer's choice; the acceptance check is that `frappe.get_print("Fees", <name>, print_format="K12 Fee Receipt")` renders without error (add this as an assertion inside `test_send_marks_last_reminder_and_respects_repeat` or a fourth mini-test if convenient — if a fourth test is added, final counts shift by +1; report actuals).

- [ ] **Step 4:** migrate; module → 3 OK (or 4 — report); full suite → 64 green (adjust if +1).
- [ ] **Step 5: Commit** `feat: overdue fee reminder emails and fee receipt print format`. Push; CI green.

---

### Task 8: Provisioning + Phase 3 wrap-up

**Files:**
- Modify: `ops/provision_school.py`, `ops/tests/test_provision_school.py`, `README.md`

- [ ] **Step 1: failing ops test** — assert a `bench execute education_k12.setup.install.ensure_fee_categories` command appears after install-apps (mirror the grade-seed test pattern). Run → FAIL. Implement (append alongside the grade-seed step). → 8 ops tests pass.
- [ ] **Step 2: full verification** — backend full suite (expect ~64; report actual), ops 8, frontend 6, `npm run build`.
- [ ] **Step 3: README** — "Phase 3 (Fees + Billing)" section: enrichment behavior (transport/sibling/VAT as components; UAE tuition-exempt default and the per-category `taxable` flag), gateway config (K12 Settings select; Mock default; Stripe keys in site_config + webhook URL `/api/method/education_k12.api.fees.stripe_webhook`; honest note that Stripe is stub-tested, needs live test-mode verification), reminders config, receipt print format, portal fees page. Update test counts. Link this plan.
- [ ] **Step 4: Commit** `feat: provision fee categories; Phase 3 docs` + push + CI green.

---

## Self-review checklist

1. Spec coverage: installment plans — NOT a separate engine: upstream Fee Schedule already issues multiple dated Fees per term (one per due date); README documents this as the installment mechanism. Sibling discounts ✔ T2. VAT ✔ T2 (component-row approach). Transport fees ✔ T2. Pluggable gateway + first concrete adapter ✔ T3/T4 (Mock verified, Stripe stub-tested — honest scope note in plan header). Receipts ✔ T5/T7. Reminders ✔ T7. Portal pay flow ✔ T5/T6. SaaS billing manual ✔ (untouched).
2. Cross-task names: `get_gateway`, `create_checkout_for`, `consume_token`, `record_fee_payment`, `complete_mock_payment`, endpoint URLs in portal.js/ChildFees.vue match api/fees.py.
3. Test math restated: backend 40→43 (T1) →48 (T2) →54 (T3) →57 (T4) →61 (T5) →64 (T7, ±1 if receipt assertion becomes a 4th test); ops 7→8; frontend 6.
