# Phase 1 — Core SIS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The K-12 student-information core: grade structure on Programs, Gulf-specific student fields, sibling linking, homeroom sections, admission document checklist, year-end promotion tool — plus the first real portal pages (teacher homeroom roster, parent children overview).

**Architecture:** Everything extends unmodified upstream doctypes via custom fields (created idempotently on install/migrate), doc-event hooks, and new doctypes in the `Education K12` module. Portal features ride whitelisted APIs in `education_k12/api/` with explicit per-record authorization (session user → Guardian/Instructor mapping), consumed by the existing Vue SPA.

**Tech Stack:** Frappe v15 (education v15.2, erpnext v15), Python 3.11, Vue 3 + frappe-ui + vue-i18n, vitest, FrappeTestCase.

**Spec:** `docs/superpowers/specs/2026-06-12-k12-education-saas-design.md` (Phase 1 section)

---

## Environment (as built in Phase 0 — see README for full detail)

- Repo (Windows): `C:\Users\asifm\source\repos\frappe-education-k12`; bench (WSL): `~/frappe-bench-dev`, port 8002, site `dev.localhost`. NEVER touch `~/frappe-bench` (unrelated production bench).
- WSL invoke pattern: `wsl -d Ubuntu -- bash -lc "export PATH=$HOME/.local/bin:$PATH; cd ~/frappe-bench-dev && <cmd>"`. Redis first: `redis-cli ping || redis-server --daemonize yes`.
- Backend tests: `bench --site dev.localhost run-tests --app education_k12` (or `--module <path>` for one module). Migrate after doctype/custom-field changes: `bench --site dev.localhost migrate`.
- Frontend: npm on Windows from `apps/education_k12/frontend` (`npm test`, `npm run build`, `npm run dev`).
- Commit from Windows; every task ends pushed with CI green (3 jobs). Commit trailer: blank line + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## Verified upstream facts this plan builds on (education v15.2)

- **Student**: `first_name`, `student_name`, `user`, `nationality` (Data), `gender`, `date_of_birth`, `blood_group`, `guardians` (Table → Student Guardian), `siblings` (Table → Student Sibling), `enabled`.
- **Student Sibling** (child): `student` (Link Student), `full_name`, `gender`, `date_of_birth`, `studying_in_same_institute` (Select `NO`/`YES`), `institution`, `program` (Data).
- **Student Guardian** (child, on Student and Student Applicant): `guardian` (Link Guardian) + relation.
- **Guardian**: `guardian_name`, `user` (Link User), `students` (Table Guardian Student).
- **Instructor**: `instructor_name`, `employee`, `status` — **no `user` field** (we add one).
- **Student Group**: `academic_year`, `group_based_on` (Select ``/`Batch`/`Course`/`Activity`), `student_group_name`, `program`, `batch`, `disabled`, `students` (Table Student Group Student: `student`, `student_name`, `group_roll_number`, `active`), `instructors` (Table Student Group Instructor).
- **Program**: `program_name` (autoname field), `program_abbreviation`, `courses`.
- **Program Enrollment** (submittable): `student`, `program`, `academic_year`, `academic_term`, `enrollment_date`, `student_name` (read only).
- **Student Applicant**: `first_name`, `program`, `application_status` (Select `Applied`/`Approved`/`Rejected`/`Admitted`), `academic_year`, `guardians`, `siblings`.
- **Academic Year**: `academic_year_name`, `year_start_date`, `year_end_date`.
- Roles shipped by education: `Academics User`, `Education Manager`, `Instructor`, `Student` — **no Guardian role** (we ensure one).

## File map (created/modified across tasks)

```
apps/education_k12/education_k12/
├── hooks.py                                  # doc_events, after_install/after_migrate (T1..T6)
├── setup/
│   ├── __init__.py
│   └── install.py                            # CUSTOM_FIELDS + ensure_customizations (T1,T2,T4,T5)
├── k12_sis/
│   ├── __init__.py
│   ├── grades.py                             # grade catalogue + create_default_grade_programs (T1)
│   ├── siblings.py                           # reciprocal sibling sync (T3)
│   ├── homeroom.py                           # homeroom validation (T4)
│   ├── admission.py                          # document checklist hooks (T5)
│   └── tests/  __init__.py, test_grades.py, test_siblings.py,
│               test_homeroom.py, test_admission.py, test_portal_api.py
├── api/
│   ├── __init__.py
│   └── portal.py                             # whitelisted portal endpoints (T7)
└── education_k12/doctype/
    ├── k12_admission_document_type/          # master (T5)
    ├── k12_admission_document/               # child table (T5)
    ├── student_promotion/                    # submittable tool (T6)
    └── student_promotion_student/            # child table (T6)

apps/education_k12/frontend/src/
├── data/portal.js                            # createResource wrappers (T8)
├── data/homeRoute.js + homeRoute.test.js     # pure role→route helper, TDD (T8)
├── pages/Home.vue                            # becomes role dispatcher (T8)
├── pages/teacher/Homerooms.vue, HomeroomRoster.vue   (T8)
├── pages/parent/Children.vue, ChildProfile.vue       (T9)
├── router.js                                 # new routes (T8, T9)
└── i18n/locales/en.json, ar.json             # new keys (T8, T9)

ops/provision_school.py + ops/tests/...       # grade seeding step (T10)
README.md                                     # Phase 1 notes (T10)
```

General test-writing notes (apply to every backend task):
- Tests are `FrappeTestCase` subclasses; they run inside a transaction that is rolled back, so create whatever records you need inline.
- Shared helpers live in `k12_sis/tests/utils.py` (created in Task 1, extended as needed). Helpers must be idempotent (`if frappe.db.exists(...) return name`).
- Run a single module while iterating: `bench --site dev.localhost run-tests --module education_k12.k12_sis.tests.test_grades`.

---

### Task 1: Custom-field infrastructure + grade structure on Program

**Files:**
- Create: `apps/education_k12/education_k12/setup/__init__.py` (empty)
- Create: `apps/education_k12/education_k12/setup/install.py`
- Create: `apps/education_k12/education_k12/k12_sis/__init__.py` (empty)
- Create: `apps/education_k12/education_k12/k12_sis/grades.py`
- Create: `apps/education_k12/education_k12/k12_sis/tests/__init__.py` (empty)
- Create: `apps/education_k12/education_k12/k12_sis/tests/utils.py`
- Test: `apps/education_k12/education_k12/k12_sis/tests/test_grades.py`
- Modify: `apps/education_k12/education_k12/hooks.py`

- [ ] **Step 1: Write the failing tests** — `test_grades.py`:

```python
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
```

And the shared helper file `k12_sis/tests/utils.py` (used by later tasks; minimal now):

```python
import frappe


def ensure_academic_year(name="2026-27", start="2026-09-01", end="2027-06-30"):
    if frappe.db.exists("Academic Year", name):
        return name
    return (
        frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": name,
                "year_start_date": start,
                "year_end_date": end,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_student(first_name, **extra):
    existing = frappe.db.get_value("Student", {"first_name": first_name})
    if existing:
        return existing
    doc = frappe.get_doc(
        {
            "doctype": "Student",
            "first_name": first_name,
            "student_email_id": f"{first_name.lower().replace(' ', '.')}@test.k12.local",
            **extra,
        }
    )
    return doc.insert(ignore_permissions=True).name
```

(If Student requires `joining_date` or rejects missing email on this education version, extend `ensure_student` accordingly — keep it the single place test students are made.)

- [ ] **Step 2: Run tests to verify they fail**

```
wsl: bench --site dev.localhost run-tests --module education_k12.k12_sis.tests.test_grades
```

Expected: ImportError (`education_k12.k12_sis.grades` missing). After creating empty package `__init__.py`s, re-run → ImportError on names. Record output.

- [ ] **Step 3: Implement** — `setup/install.py`:

```python
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

K12_ROLES = ("Guardian",)

CUSTOM_FIELDS = {
    "Program": [
        dict(
            fieldname="k12_grade_section",
            fieldtype="Section Break",
            label="K-12 Grade",
            insert_after="program_abbreviation",
        ),
        dict(
            fieldname="is_k12_grade",
            fieldtype="Check",
            label="Is K-12 Grade",
            insert_after="k12_grade_section",
        ),
        dict(
            fieldname="grade_order",
            fieldtype="Int",
            label="Grade Order",
            insert_after="is_k12_grade",
            depends_on="is_k12_grade",
        ),
        dict(
            fieldname="grade_band",
            fieldtype="Select",
            label="Grade Band",
            options="\nKG\nPrimary\nMiddle\nSecondary",
            insert_after="grade_order",
            depends_on="is_k12_grade",
        ),
    ],
}


def ensure_customizations():
    """Idempotent: runs on install and on every migrate."""
    create_custom_fields(CUSTOM_FIELDS, ignore_validate=True)
    ensure_roles()


def ensure_roles():
    for role in K12_ROLES:
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {"doctype": "Role", "role_name": role, "desk_access": 0}
            ).insert(ignore_permissions=True)
```

`k12_sis/grades.py`:

```python
"""K-12 grade catalogue mapped onto upstream Programs."""

import frappe

# (program_name, grade_band, grade_order)
GRADE_LEVELS = [
    ("KG 1", "KG", 1),
    ("KG 2", "KG", 2),
    ("Grade 1", "Primary", 3),
    ("Grade 2", "Primary", 4),
    ("Grade 3", "Primary", 5),
    ("Grade 4", "Primary", 6),
    ("Grade 5", "Primary", 7),
    ("Grade 6", "Middle", 8),
    ("Grade 7", "Middle", 9),
    ("Grade 8", "Middle", 10),
    ("Grade 9", "Secondary", 11),
    ("Grade 10", "Secondary", 12),
    ("Grade 11", "Secondary", 13),
    ("Grade 12", "Secondary", 14),
]


def create_default_grade_programs():
    """Create the standard KG1-G12 Programs. Idempotent; returns created names."""
    created = []
    for program_name, band, order in GRADE_LEVELS:
        if frappe.db.exists("Program", program_name):
            continue
        frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": program_name,
                "is_k12_grade": 1,
                "grade_band": band,
                "grade_order": order,
            }
        ).insert(ignore_permissions=True)
        created.append(program_name)
    return created
```

`hooks.py` — add (uncomment/insert near the commented install hooks):

```python
after_install = ["education_k12.setup.install.ensure_customizations"]
after_migrate = ["education_k12.setup.install.ensure_customizations"]
```

- [ ] **Step 4: Migrate and run tests to verify they pass**

```
wsl: bench --site dev.localhost migrate
wsl: bench --site dev.localhost run-tests --module education_k12.k12_sis.tests.test_grades
```

Expected: `Ran 3 tests ... OK`. Also verify the Guardian role: `bench --site dev.localhost execute frappe.db.exists --args '["Role","Guardian"]'` → truthy.

- [ ] **Step 5: Commit**

```
git add apps/education_k12/education_k12
git commit -m "feat: K-12 grade structure on Program with idempotent custom-field setup"
git push
```

---

### Task 2: Gulf-specific student fields

**Files:**
- Modify: `apps/education_k12/education_k12/setup/install.py` (extend CUSTOM_FIELDS)
- Test: `apps/education_k12/education_k12/k12_sis/tests/test_gulf_fields.py`

- [ ] **Step 1: Write the failing test** — `test_gulf_fields.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

GULF_FIELDS = (
    "national_id",
    "national_id_expiry",
    "visa_number",
    "visa_expiry",
    "emergency_contact_name",
    "emergency_contact_phone",
    "medical_conditions",
)


class TestGulfFields(FrappeTestCase):
    def test_student_has_gulf_fields(self):
        meta = frappe.get_meta("Student")
        for fieldname in GULF_FIELDS:
            self.assertTrue(
                meta.has_field(fieldname), f"Student is missing custom field {fieldname}"
            )

    def test_applicant_has_identity_fields(self):
        meta = frappe.get_meta("Student Applicant")
        for fieldname in ("national_id", "national_id_expiry"):
            self.assertTrue(
                meta.has_field(fieldname),
                f"Student Applicant is missing custom field {fieldname}",
            )
```

- [ ] **Step 2: Run → fails** (fields missing). Record output.

- [ ] **Step 3: Implement** — extend `CUSTOM_FIELDS` in `setup/install.py`:

```python
    "Student": [
        dict(
            fieldname="k12_identity_section",
            fieldtype="Section Break",
            label="Identity & Visa",
            insert_after="nationality",
        ),
        dict(
            fieldname="national_id",
            fieldtype="Data",
            label="National ID (Emirates ID / Iqama)",
            insert_after="k12_identity_section",
        ),
        dict(
            fieldname="national_id_expiry",
            fieldtype="Date",
            label="National ID Expiry",
            insert_after="national_id",
        ),
        dict(
            fieldname="visa_number",
            fieldtype="Data",
            label="Visa Number",
            insert_after="national_id_expiry",
        ),
        dict(
            fieldname="visa_expiry",
            fieldtype="Date",
            label="Visa Expiry",
            insert_after="visa_number",
        ),
        dict(
            fieldname="k12_welfare_section",
            fieldtype="Section Break",
            label="Emergency & Medical",
            insert_after="visa_expiry",
        ),
        dict(
            fieldname="emergency_contact_name",
            fieldtype="Data",
            label="Emergency Contact Name",
            insert_after="k12_welfare_section",
        ),
        dict(
            fieldname="emergency_contact_phone",
            fieldtype="Data",
            label="Emergency Contact Phone",
            insert_after="emergency_contact_name",
        ),
        dict(
            fieldname="medical_conditions",
            fieldtype="Small Text",
            label="Medical Conditions / Allergies",
            insert_after="emergency_contact_phone",
        ),
    ],
    "Student Applicant": [
        dict(
            fieldname="national_id",
            fieldtype="Data",
            label="National ID (Emirates ID / Iqama)",
            insert_after="nationality",
        ),
        dict(
            fieldname="national_id_expiry",
            fieldtype="Date",
            label="National ID Expiry",
            insert_after="national_id",
        ),
    ],
```

- [ ] **Step 4: Migrate, run → 2 tests OK.** Also re-run test_grades (still OK).

- [ ] **Step 5: Commit** — `feat: Gulf identity, visa, emergency and medical fields on Student`

---

### Task 3: Sibling reciprocal sync

**Files:**
- Create: `apps/education_k12/education_k12/k12_sis/siblings.py`
- Test: `apps/education_k12/education_k12/k12_sis/tests/test_siblings.py`
- Modify: `apps/education_k12/education_k12/hooks.py` (doc_events)

- [ ] **Step 1: Write the failing tests** — `test_siblings.py`:

```python
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
```

- [ ] **Step 2: Run → fails** (no reciprocal row; no self-check). Record output.

- [ ] **Step 3: Implement** — `k12_sis/siblings.py`:

```python
import frappe
from frappe import _


def validate_siblings(doc, method=None):
    for row in doc.siblings:
        if row.student == doc.name:
            frappe.throw(_("A student cannot be their own sibling"))


def sync_reciprocal_siblings(doc, method=None):
    """Ensure every in-school sibling also lists this student back."""
    for row in doc.siblings:
        if not row.student or row.studying_in_same_institute != "YES":
            continue
        sibling = frappe.get_doc("Student", row.student)
        if any(s.student == doc.name for s in sibling.siblings):
            continue
        sibling.append(
            "siblings",
            {
                "student": doc.name,
                "full_name": doc.student_name or doc.first_name,
                "gender": doc.gender,
                "date_of_birth": doc.date_of_birth,
                "studying_in_same_institute": "YES",
            },
        )
        sibling.save(ignore_permissions=True)
```

`hooks.py`:

```python
doc_events = {
    "Student": {
        "validate": "education_k12.k12_sis.siblings.validate_siblings",
        "on_update": "education_k12.k12_sis.siblings.sync_reciprocal_siblings",
    },
}
```

(Recursion is bounded: B's save triggers sync for B, sees A already listed, stops.)

- [ ] **Step 4: Run → 3 tests OK** (plus previous modules still OK).

- [ ] **Step 5: Commit** — `feat: reciprocal sibling linking on Student`

---

### Task 4: Homeroom sections + Instructor user mapping

**Files:**
- Create: `apps/education_k12/education_k12/k12_sis/homeroom.py`
- Test: `apps/education_k12/education_k12/k12_sis/tests/test_homeroom.py`
- Modify: `setup/install.py` (CUSTOM_FIELDS for Student Group + Instructor), `hooks.py` (doc_events)

- [ ] **Step 1: Write the failing tests** — `test_homeroom.py`:

```python
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
```

- [ ] **Step 2: Run → fails** (fields missing). Record output.

- [ ] **Step 3: Implement** — extend `CUSTOM_FIELDS`:

```python
    "Student Group": [
        dict(
            fieldname="is_homeroom",
            fieldtype="Check",
            label="Is Homeroom",
            insert_after="group_based_on",
        ),
        dict(
            fieldname="homeroom_teacher",
            fieldtype="Link",
            options="Instructor",
            label="Homeroom Teacher",
            insert_after="is_homeroom",
            depends_on="is_homeroom",
        ),
    ],
    "Instructor": [
        dict(
            fieldname="user",
            fieldtype="Link",
            options="User",
            label="User",
            insert_after="employee",
            unique=1,
        ),
    ],
```

`k12_sis/homeroom.py`:

```python
import frappe
from frappe import _


def validate_homeroom(doc, method=None):
    if not doc.is_homeroom:
        return
    if not doc.homeroom_teacher:
        frappe.throw(_("A homeroom must have a Homeroom Teacher"))
```

`hooks.py` doc_events — add:

```python
    "Student Group": {
        "validate": "education_k12.k12_sis.homeroom.validate_homeroom",
    },
```

- [ ] **Step 4: Migrate, run → 3 tests OK.**
- [ ] **Step 5: Commit** — `feat: homeroom sections on Student Group and Instructor user mapping`

---

### Task 5: Admission document checklist

**Files:**
- Create doctype `K12 Admission Document Type` (master): `education_k12/doctype/k12_admission_document_type/` (`__init__.py`, json, py)
- Create doctype `K12 Admission Document` (child): `education_k12/doctype/k12_admission_document/`
- Create: `k12_sis/admission.py`
- Test: `k12_sis/tests/test_admission.py`
- Modify: `setup/install.py` (Table custom field on Student Applicant), `hooks.py` (doc_events)

- [ ] **Step 1: Write the failing tests** — `test_admission.py`:

```python
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


def make_applicant(first_name="Applicant One"):
    return frappe.get_doc(
        {
            "doctype": "Student Applicant",
            "first_name": first_name,
            "academic_year": ensure_academic_year(),
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
```

- [ ] **Step 2: Run → fails** (doctype missing). Record output.

- [ ] **Step 3: Create doctypes.**

`k12_admission_document_type.json`:

```json
{
 "actions": [],
 "autoname": "field:document_name",
 "creation": "2026-06-12 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["document_name", "mandatory"],
 "fields": [
  {"fieldname": "document_name", "fieldtype": "Data", "label": "Document Name", "reqd": 1, "unique": 1},
  {"fieldname": "mandatory", "fieldtype": "Check", "label": "Mandatory", "default": "1"}
 ],
 "links": [],
 "modified": "2026-06-12 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Admission Document Type",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_admission_document.json` (child):

```json
{
 "actions": [],
 "creation": "2026-06-12 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["document_type", "status", "attachment"],
 "fields": [
  {"fieldname": "document_type", "fieldtype": "Link", "options": "K12 Admission Document Type", "label": "Document", "reqd": 1, "in_list_view": 1},
  {"fieldname": "status", "fieldtype": "Select", "options": "Pending\nReceived\nVerified", "default": "Pending", "label": "Status", "in_list_view": 1},
  {"fieldname": "attachment", "fieldtype": "Attach", "label": "Attachment", "in_list_view": 1}
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-06-12 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Admission Document",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

Both `.py` controllers are `class ...(Document): pass` like K12 Settings. Add to `CUSTOM_FIELDS`:

```python
    "Student Applicant": [
        # ...existing identity fields from Task 2...
        dict(
            fieldname="k12_documents_section",
            fieldtype="Section Break",
            label="Admission Documents",
            insert_after="application_status",
        ),
        dict(
            fieldname="admission_documents",
            fieldtype="Table",
            options="K12 Admission Document",
            label="Admission Documents",
            insert_after="k12_documents_section",
        ),
    ],
```

`k12_sis/admission.py`:

```python
import frappe
from frappe import _


def populate_admission_documents(doc, method=None):
    """Seed the mandatory-document checklist on new applicants (before_insert)."""
    existing = {row.document_type for row in doc.admission_documents}
    mandatory = frappe.get_all(
        "K12 Admission Document Type", filters={"mandatory": 1}, pluck="name"
    )
    for doc_type in mandatory:
        if doc_type not in existing:
            doc.append(
                "admission_documents", {"document_type": doc_type, "status": "Pending"}
            )


def warn_pending_documents(doc, method=None):
    """Non-blocking nudge when approving/admitting with pending mandatory docs."""
    if doc.application_status not in ("Approved", "Admitted"):
        return
    mandatory = set(
        frappe.get_all(
            "K12 Admission Document Type", filters={"mandatory": 1}, pluck="name"
        )
    )
    pending = [
        row.document_type
        for row in doc.admission_documents
        if row.status == "Pending" and row.document_type in mandatory
    ]
    if pending:
        frappe.msgprint(
            _("Mandatory admission documents still pending: {0}").format(
                ", ".join(pending)
            ),
            indicator="orange",
        )
```

`hooks.py` doc_events — add:

```python
    "Student Applicant": {
        "before_insert": "education_k12.k12_sis.admission.populate_admission_documents",
        "validate": "education_k12.k12_sis.admission.warn_pending_documents",
    },
```

- [ ] **Step 4: Migrate, run → 2 tests OK.**
- [ ] **Step 5: Commit** — `feat: admission document checklist on Student Applicant`

---

### Task 6: Student Promotion tool

**Files:**
- Create doctype `Student Promotion Student` (child): `education_k12/doctype/student_promotion_student/`
- Create doctype `Student Promotion` (submittable): `education_k12/doctype/student_promotion/`
- Test: `education_k12/doctype/student_promotion/test_student_promotion.py`

- [ ] **Step 1: Write the failing tests** — `test_student_promotion.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.grades import create_default_grade_programs
from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


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
```

- [ ] **Step 2: Run → fails** (doctype missing). Record output.

- [ ] **Step 3: Create doctypes.**

`student_promotion_student.json` (child):

```json
{
 "actions": [],
 "creation": "2026-06-12 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["student", "student_name", "current_enrollment", "action"],
 "fields": [
  {"fieldname": "student", "fieldtype": "Link", "options": "Student", "label": "Student", "reqd": 1, "in_list_view": 1},
  {"fieldname": "student_name", "fieldtype": "Data", "label": "Student Name", "fetch_from": "student.student_name", "in_list_view": 1},
  {"fieldname": "current_enrollment", "fieldtype": "Link", "options": "Program Enrollment", "label": "Current Enrollment", "read_only": 1},
  {"fieldname": "action", "fieldtype": "Select", "options": "Promote\nRetain\nExit", "default": "Promote", "label": "Action", "reqd": 1, "in_list_view": 1}
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-06-12 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "Student Promotion Student",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`student_promotion.json` (submittable; `is_submittable: 1`, naming `format:K12-PROM-{YYYY}-{#####}`):

```json
{
 "actions": [],
 "autoname": "format:K12-PROM-{YYYY}-{#####}",
 "creation": "2026-06-12 12:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["from_academic_year", "from_program", "to_academic_year", "to_program", "fetch_students", "students", "amended_from"],
 "fields": [
  {"fieldname": "from_academic_year", "fieldtype": "Link", "options": "Academic Year", "label": "From Academic Year", "reqd": 1},
  {"fieldname": "from_program", "fieldtype": "Link", "options": "Program", "label": "From Grade/Program", "reqd": 1},
  {"fieldname": "to_academic_year", "fieldtype": "Link", "options": "Academic Year", "label": "To Academic Year", "reqd": 1},
  {"fieldname": "to_program", "fieldtype": "Link", "options": "Program", "label": "To Grade/Program"},
  {"fieldname": "fetch_students", "fieldtype": "Button", "label": "Get Students"},
  {"fieldname": "students", "fieldtype": "Table", "options": "Student Promotion Student", "label": "Students"},
  {"fieldname": "amended_from", "fieldtype": "Link", "options": "Student Promotion", "label": "Amended From", "no_copy": 1, "print_hide": 1, "read_only": 1}
 ],
 "is_submittable": 1,
 "links": [],
 "modified": "2026-06-12 12:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "Student Promotion",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "submit": 1, "cancel": 1, "amend": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1, "write": 1, "create": 1, "submit": 1, "email": 1, "print": 1, "share": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`student_promotion.py`:

```python
import frappe
from frappe import _
from frappe.model.document import Document


class StudentPromotion(Document):
    def validate(self):
        if self.from_academic_year == self.to_academic_year:
            frappe.throw(_("From and To academic years must differ"))
        promote_rows = [r for r in self.students if r.action == "Promote"]
        if promote_rows:
            if not self.to_program:
                frappe.throw(_("To Grade/Program is required to promote students"))
            if self.to_program == self.from_program:
                frappe.throw(_("To Grade/Program must differ from the current grade"))

    @frappe.whitelist()
    def get_students(self):
        enrollments = frappe.get_all(
            "Program Enrollment",
            filters={
                "program": self.from_program,
                "academic_year": self.from_academic_year,
                "docstatus": 1,
            },
            fields=["name", "student", "student_name"],
            order_by="student_name asc",
        )
        self.set("students", [])
        for enrollment in enrollments:
            self.append(
                "students",
                {
                    "student": enrollment.student,
                    "student_name": enrollment.student_name,
                    "current_enrollment": enrollment.name,
                    "action": "Promote",
                },
            )
        return self

    def on_submit(self):
        for row in self.students:
            if row.action == "Exit":
                continue
            target_program = (
                self.to_program if row.action == "Promote" else self.from_program
            )
            if frappe.db.exists(
                "Program Enrollment",
                {
                    "student": row.student,
                    "program": target_program,
                    "academic_year": self.to_academic_year,
                    "docstatus": ("<", 2),
                },
            ):
                continue
            enrollment = frappe.get_doc(
                {
                    "doctype": "Program Enrollment",
                    "student": row.student,
                    "program": target_program,
                    "academic_year": self.to_academic_year,
                    "enrollment_date": frappe.utils.today(),
                }
            )
            enrollment.insert(ignore_permissions=True)
            enrollment.submit()
```

(If upstream Program Enrollment validation demands extra fields — e.g. academic term or applicant — adapt `enroll`/`on_submit` minimally and note it; do not weaken the assertions.)

- [ ] **Step 4: Migrate, run → 4 tests OK.**
- [ ] **Step 5: Commit** — `feat: year-end Student Promotion tool`

---

### Task 7: Portal API layer with per-record authorization

**Files:**
- Create: `apps/education_k12/education_k12/api/__init__.py` (empty)
- Create: `apps/education_k12/education_k12/api/portal.py`
- Test: `apps/education_k12/education_k12/k12_sis/tests/test_portal_api.py`

- [ ] **Step 1: Write the failing tests** — `test_portal_api.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.api import portal
from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student


def ensure_user(email, first_name, roles=()):
    if not frappe.db.exists("User", email):
        frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": first_name,
                "send_welcome_email": 0,
                "roles": [{"role": r} for r in roles],
            }
        ).insert(ignore_permissions=True)
    return email


def ensure_guardian(name, user_email):
    existing = frappe.db.get_value("Guardian", {"user": user_email})
    if existing:
        return existing
    return (
        frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_name": name,
                "email_address": user_email,
                "user": user_email,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def link_guardian_to_student(student, guardian):
    doc = frappe.get_doc("Student", student)
    if guardian not in [g.guardian for g in doc.guardians]:
        doc.append("guardians", {"guardian": guardian, "relation": "Father"})
        doc.save(ignore_permissions=True)


def ensure_teacher(name, user_email):
    existing = frappe.db.get_value("Instructor", {"user": user_email})
    if existing:
        return existing
    return (
        frappe.get_doc(
            {"doctype": "Instructor", "instructor_name": name, "user": user_email}
        )
        .insert(ignore_permissions=True)
        .name
    )


def make_homeroom(name, teacher, students=()):
    group = frappe.get_doc(
        {
            "doctype": "Student Group",
            "student_group_name": name,
            "academic_year": ensure_academic_year(),
            "group_based_on": "Activity",
            "is_homeroom": 1,
            "homeroom_teacher": teacher,
        }
    )
    for index, student in enumerate(students, start=1):
        group.append(
            "students", {"student": student, "group_roll_number": index, "active": 1}
        )
    group.insert(ignore_permissions=True)
    return group.name


class TestPortalAPI(FrappeTestCase):
    def tearDown(self):
        frappe.set_user("Administrator")
        super().tearDown()

    def test_guardian_sees_only_own_children(self):
        child_a = ensure_student("Portal Child A")
        child_b = ensure_student("Portal Child B")
        user_a = ensure_user("parent.a@test.k12.local", "Parent A", roles=("Guardian",))
        user_b = ensure_user("parent.b@test.k12.local", "Parent B", roles=("Guardian",))
        link_guardian_to_student(child_a, ensure_guardian("Parent A", user_a))
        link_guardian_to_student(child_b, ensure_guardian("Parent B", user_b))

        frappe.set_user(user_a)
        children = portal.get_children()
        names = [c["name"] for c in children]
        self.assertIn(child_a, names)
        self.assertNotIn(child_b, names)

    def test_guardian_cannot_read_other_child_profile(self):
        child_b = ensure_student("Portal Child B2")
        user_a = ensure_user("parent.a2@test.k12.local", "Parent A2", roles=("Guardian",))
        user_b = ensure_user("parent.b2@test.k12.local", "Parent B2", roles=("Guardian",))
        ensure_guardian("Parent A2", user_a)
        link_guardian_to_student(child_b, ensure_guardian("Parent B2", user_b))

        frappe.set_user(user_a)
        with self.assertRaises(frappe.PermissionError):
            portal.get_child_profile(child_b)

    def test_teacher_sees_only_own_homerooms(self):
        s1 = ensure_student("Roster Kid One")
        t1_user = ensure_user("teacher.one@test.k12.local", "Teacher One")
        t2_user = ensure_user("teacher.two@test.k12.local", "Teacher Two")
        t1 = ensure_teacher("Teacher One", t1_user)
        t2 = ensure_teacher("Teacher Two", t2_user)
        own = make_homeroom("HR Own 1", t1, students=(s1,))
        other = make_homeroom("HR Other 1", t2)

        frappe.set_user(t1_user)
        homerooms = [g["name"] for g in portal.get_homerooms()]
        self.assertIn(own, homerooms)
        self.assertNotIn(other, homerooms)

        roster = portal.get_homeroom_roster(own)
        self.assertIn(s1, [r["student"] for r in roster["students"]])

        with self.assertRaises(frappe.PermissionError):
            portal.get_homeroom_roster(other)

    def test_context_reports_role(self):
        t_user = ensure_user("teacher.ctx@test.k12.local", "Teacher Ctx")
        ensure_teacher("Teacher Ctx", t_user)
        frappe.set_user(t_user)
        context = portal.get_portal_context()
        self.assertTrue(context["is_teacher"])
        self.assertFalse(context["is_guardian"])

    def test_guest_is_rejected(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            portal.get_portal_context()
```

- [ ] **Step 2: Run → fails** (module missing). Record output.

- [ ] **Step 3: Implement** — `api/portal.py`:

```python
"""Whitelisted portal endpoints.

Authorization model: the session user is mapped to a Guardian (via
Guardian.user) or an Instructor (via the Instructor.user custom field).
Every endpoint authorizes per record — a guardian can only read their own
children; a teacher only their own homerooms. Data reads use frappe.db
directly (bypassing role permissions) AFTER the explicit ownership check.
"""

import frappe
from frappe import _


def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Login required"), frappe.PermissionError)


def _guardian():
    _require_login()
    name = frappe.db.get_value("Guardian", {"user": frappe.session.user})
    if not name:
        frappe.throw(_("Not registered as a guardian"), frappe.PermissionError)
    return name


def _instructor():
    _require_login()
    name = frappe.db.get_value("Instructor", {"user": frappe.session.user})
    if not name:
        frappe.throw(_("Not registered as an instructor"), frappe.PermissionError)
    return name


def _children_of(guardian):
    return frappe.get_all(
        "Student Guardian",
        filters={"guardian": guardian, "parenttype": "Student"},
        pluck="parent",
    )


@frappe.whitelist()
def get_portal_context():
    _require_login()
    user = frappe.session.user
    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name"),
        "is_teacher": bool(frappe.db.get_value("Instructor", {"user": user})),
        "is_guardian": bool(frappe.db.get_value("Guardian", {"user": user})),
    }


@frappe.whitelist()
def get_children():
    guardian = _guardian()
    students = frappe.get_all(
        "Student",
        filters={"name": ("in", _children_of(guardian)), "enabled": 1},
        fields=["name", "student_name", "image", "date_of_birth"],
        order_by="student_name asc",
    )
    for student in students:
        student["enrollment"] = _current_enrollment(student["name"])
    return students


def _current_enrollment(student):
    rows = frappe.get_all(
        "Program Enrollment",
        filters={"student": student, "docstatus": 1},
        fields=["program", "academic_year"],
        order_by="enrollment_date desc",
        limit=1,
    )
    return rows[0] if rows else None


@frappe.whitelist()
def get_child_profile(student):
    guardian = _guardian()
    if student not in _children_of(guardian):
        frappe.throw(_("Not your child"), frappe.PermissionError)
    profile = frappe.db.get_value(
        "Student",
        student,
        [
            "name",
            "student_name",
            "image",
            "date_of_birth",
            "nationality",
            "blood_group",
            "medical_conditions",
            "emergency_contact_name",
            "emergency_contact_phone",
        ],
        as_dict=True,
    )
    profile["enrollment"] = _current_enrollment(student)
    profile["homeroom"] = frappe.db.get_value(
        "Student Group Student",
        {"student": student, "parenttype": "Student Group", "active": 1},
        "parent",
    )
    return profile


@frappe.whitelist()
def get_homerooms():
    instructor = _instructor()
    return frappe.get_all(
        "Student Group",
        filters={"homeroom_teacher": instructor, "is_homeroom": 1, "disabled": 0},
        fields=["name", "student_group_name", "program", "batch", "academic_year"],
        order_by="student_group_name asc",
    )


@frappe.whitelist()
def get_homeroom_roster(student_group):
    instructor = _instructor()
    group = frappe.db.get_value(
        "Student Group",
        student_group,
        ["name", "student_group_name", "homeroom_teacher", "is_homeroom", "program"],
        as_dict=True,
    )
    if not group or not group.is_homeroom or group.homeroom_teacher != instructor:
        frappe.throw(_("Not your homeroom"), frappe.PermissionError)
    students = frappe.get_all(
        "Student Group Student",
        filters={"parent": student_group, "parenttype": "Student Group", "active": 1},
        fields=["student", "student_name", "group_roll_number"],
        order_by="group_roll_number asc",
    )
    return {"group": group, "students": students}
```

- [ ] **Step 4: Run → 5 tests OK.** Run the whole app suite too (`run-tests --app education_k12`) — everything green.
- [ ] **Step 5: Commit** — `feat: portal API layer with per-record guardian/teacher authorization`

---

### Task 8: Portal — role-aware home + teacher homeroom pages

**Files (all under `apps/education_k12/frontend/src/`):**
- Create: `data/portal.js`, `data/homeRoute.js`
- Test: `data/homeRoute.test.js`
- Create: `pages/teacher/Homerooms.vue`, `pages/teacher/HomeroomRoster.vue`
- Modify: `pages/Home.vue`, `router.js`, `i18n/locales/en.json`, `i18n/locales/ar.json`

- [ ] **Step 1: TDD the route helper** — `data/homeRoute.test.js`:

```js
import { describe, it, expect } from 'vitest'
import { homeRouteFor } from './homeRoute'

describe('homeRouteFor', () => {
  it('routes teachers to homerooms', () => {
    expect(homeRouteFor({ is_teacher: true, is_guardian: false })).toBe('TeacherHomerooms')
  })
  it('routes guardians to children overview', () => {
    expect(homeRouteFor({ is_guardian: true, is_teacher: false })).toBe('Children')
  })
  it('prefers teacher when user is both', () => {
    expect(homeRouteFor({ is_teacher: true, is_guardian: true })).toBe('TeacherHomerooms')
  })
  it('falls back to NoAccess', () => {
    expect(homeRouteFor({})).toBe('NoAccess')
  })
})
```

`npm test` → fails (module missing). Implement `data/homeRoute.js`:

```js
export function homeRouteFor(context) {
  if (context?.is_teacher) return 'TeacherHomerooms'
  if (context?.is_guardian) return 'Children'
  return 'NoAccess'
}
```

`npm test` → all pass (now 6 frontend tests).

- [ ] **Step 2: Data layer** — `data/portal.js`:

```js
import { createResource } from 'frappe-ui'

export const portalContext = createResource({
  url: 'education_k12.api.portal.get_portal_context',
  cache: 'portal-context',
})

export const homerooms = createResource({
  url: 'education_k12.api.portal.get_homerooms',
  cache: 'homerooms',
})

export function homeroomRoster(groupName) {
  return createResource({
    url: 'education_k12.api.portal.get_homeroom_roster',
    params: { student_group: groupName },
    auto: true,
  })
}

export const children = createResource({
  url: 'education_k12.api.portal.get_children',
  cache: 'children',
})

export function childProfile(studentId) {
  return createResource({
    url: 'education_k12.api.portal.get_child_profile',
    params: { student: studentId },
    auto: true,
  })
}
```

- [ ] **Step 3: Home dispatcher** — replace `pages/Home.vue`:

```vue
<template>
  <div class="p-8">
    <div class="mb-6 flex items-center justify-between">
      <h1 class="text-2xl font-semibold">
        {{ $t('home.welcome') }}, {{ portalContext.data?.full_name || session.user }}
      </h1>
      <div class="flex gap-2">
        <Button @click="setLocale('en')">English</Button>
        <Button @click="setLocale('ar')">العربية</Button>
        <Button variant="outline" @click="session.logout.submit()">
          {{ $t('home.logout') }}
        </Button>
      </div>
    </div>
    <p v-if="noAccess" class="text-gray-600">{{ $t('home.noAccess') }}</p>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button } from 'frappe-ui'
import { session } from '../data/session'
import { portalContext } from '../data/portal'
import { homeRouteFor } from '../data/homeRoute'
import { setLocale } from '../i18n'

const router = useRouter()
portalContext.fetch()

const noAccess = computed(
  () => portalContext.data && homeRouteFor(portalContext.data) === 'NoAccess'
)

watch(
  () => portalContext.data,
  (context) => {
    if (!context) return
    const target = homeRouteFor(context)
    if (target !== 'NoAccess') router.replace({ name: target })
  },
  { immediate: true }
)
</script>
```

- [ ] **Step 4: Teacher pages.**

`pages/teacher/Homerooms.vue`:

```vue
<template>
  <div class="p-8">
    <h1 class="mb-4 text-2xl font-semibold">{{ $t('teacher.myHomerooms') }}</h1>
    <div v-if="homerooms.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!homerooms.data?.length" class="text-gray-600">
      {{ $t('teacher.noHomerooms') }}
    </p>
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <router-link
        v-for="group in homerooms.data"
        :key="group.name"
        :to="{ name: 'HomeroomRoster', params: { groupId: group.name } }"
        class="rounded-lg border p-4 hover:shadow"
      >
        <div class="text-lg font-medium">{{ group.student_group_name }}</div>
        <div class="text-sm text-gray-600">
          {{ group.program }} · {{ group.academic_year }}
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { homerooms } from '../../data/portal'
homerooms.fetch()
</script>
```

`pages/teacher/HomeroomRoster.vue`:

```vue
<template>
  <div class="p-8">
    <router-link class="text-sm text-blue-600" :to="{ name: 'TeacherHomerooms' }">
      ← {{ $t('teacher.myHomerooms') }}
    </router-link>
    <div v-if="roster.loading" class="mt-4 text-gray-500">{{ $t('common.loading') }}</div>
    <template v-else-if="roster.data">
      <h1 class="mb-4 mt-2 text-2xl font-semibold">
        {{ roster.data.group.student_group_name }}
      </h1>
      <table class="w-full border-collapse text-start">
        <thead>
          <tr class="border-b text-sm text-gray-600">
            <th class="py-2 text-start">{{ $t('teacher.rollNo') }}</th>
            <th class="py-2 text-start">{{ $t('teacher.studentName') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in roster.data.students" :key="row.student" class="border-b">
            <td class="py-2">{{ row.group_roll_number }}</td>
            <td class="py-2">{{ row.student_name }}</td>
          </tr>
        </tbody>
      </table>
    </template>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { homeroomRoster } from '../../data/portal'

const route = useRoute()
const roster = homeroomRoster(route.params.groupId)
</script>
```

- [ ] **Step 5: Routes** — add to `router.js` routes array:

```js
  {
    path: '/teacher/homerooms',
    name: 'TeacherHomerooms',
    component: () => import('./pages/teacher/Homerooms.vue'),
  },
  {
    path: '/teacher/homerooms/:groupId',
    name: 'HomeroomRoster',
    component: () => import('./pages/teacher/HomeroomRoster.vue'),
  },
```

- [ ] **Step 6: i18n keys** — merge into `en.json`:

```json
{
  "common": { "loading": "Loading…" },
  "home": { "noAccess": "Your account has no portal access yet. Contact the school office." },
  "teacher": {
    "myHomerooms": "My Homerooms",
    "noHomerooms": "No homerooms assigned to you yet.",
    "rollNo": "Roll #",
    "studentName": "Student"
  }
}
```

`ar.json`:

```json
{
  "common": { "loading": "جارٍ التحميل…" },
  "home": { "noAccess": "لا يملك حسابك صلاحية الوصول إلى البوابة بعد. يرجى مراجعة إدارة المدرسة." },
  "teacher": {
    "myHomerooms": "فصولي",
    "noHomerooms": "لا توجد فصول مسندة إليك بعد.",
    "rollNo": "الرقم",
    "studentName": "الطالب"
  }
}
```

- [ ] **Step 7: Verify** — `npm test` (6 pass), `npm run build` (succeeds). Manual smoke: start bench (WSL), create an Instructor with `user` = a test user + a homeroom on dev.localhost (via `bench execute` or Desk), log in as that user at `http://localhost:8002/portal`, see homeroom list and roster. Stop bench after. (If full manual smoke is impractical, verify at minimum that `/portal` still serves and the built JS references the new routes; note what was and wasn't manually verified.)

- [ ] **Step 8: Commit** — `feat: role-aware portal home and teacher homeroom pages`

---

### Task 9: Portal — parent pages

**Files:**
- Create: `pages/parent/Children.vue`, `pages/parent/ChildProfile.vue`
- Modify: `router.js`, `i18n/locales/en.json`, `i18n/locales/ar.json`

- [ ] **Step 1: Pages.**

`pages/parent/Children.vue`:

```vue
<template>
  <div class="p-8">
    <h1 class="mb-4 text-2xl font-semibold">{{ $t('parent.myChildren') }}</h1>
    <div v-if="children.loading" class="text-gray-500">{{ $t('common.loading') }}</div>
    <p v-else-if="!children.data?.length" class="text-gray-600">
      {{ $t('parent.noChildren') }}
    </p>
    <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      <router-link
        v-for="child in children.data"
        :key="child.name"
        :to="{ name: 'ChildProfile', params: { studentId: child.name } }"
        class="rounded-lg border p-4 hover:shadow"
      >
        <div class="text-lg font-medium">{{ child.student_name }}</div>
        <div v-if="child.enrollment" class="text-sm text-gray-600">
          {{ child.enrollment.program }} · {{ child.enrollment.academic_year }}
        </div>
      </router-link>
    </div>
  </div>
</template>

<script setup>
import { children } from '../../data/portal'
children.fetch()
</script>
```

`pages/parent/ChildProfile.vue`:

```vue
<template>
  <div class="p-8">
    <router-link class="text-sm text-blue-600" :to="{ name: 'Children' }">
      ← {{ $t('parent.myChildren') }}
    </router-link>
    <div v-if="profile.loading" class="mt-4 text-gray-500">{{ $t('common.loading') }}</div>
    <template v-else-if="profile.data">
      <h1 class="mb-4 mt-2 text-2xl font-semibold">{{ profile.data.student_name }}</h1>
      <dl class="grid max-w-xl grid-cols-2 gap-x-6 gap-y-3">
        <template v-for="field in profileFields" :key="field.key">
          <dt class="text-sm text-gray-600">{{ $t(field.label) }}</dt>
          <dd class="text-sm">{{ field.value() || '—' }}</dd>
        </template>
      </dl>
    </template>
  </div>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { childProfile } from '../../data/portal'

const route = useRoute()
const profile = childProfile(route.params.studentId)

const profileFields = [
  { key: 'grade', label: 'parent.grade', value: () => profile.data?.enrollment?.program },
  { key: 'year', label: 'parent.academicYear', value: () => profile.data?.enrollment?.academic_year },
  { key: 'homeroom', label: 'parent.homeroom', value: () => profile.data?.homeroom },
  { key: 'dob', label: 'parent.dateOfBirth', value: () => profile.data?.date_of_birth },
  { key: 'nationality', label: 'parent.nationality', value: () => profile.data?.nationality },
  { key: 'blood', label: 'parent.bloodGroup', value: () => profile.data?.blood_group },
  { key: 'medical', label: 'parent.medical', value: () => profile.data?.medical_conditions },
  { key: 'emName', label: 'parent.emergencyContact', value: () => profile.data?.emergency_contact_name },
  { key: 'emPhone', label: 'parent.emergencyPhone', value: () => profile.data?.emergency_contact_phone },
]
</script>
```

- [ ] **Step 2: Routes** — add:

```js
  {
    path: '/children',
    name: 'Children',
    component: () => import('./pages/parent/Children.vue'),
  },
  {
    path: '/children/:studentId',
    name: 'ChildProfile',
    component: () => import('./pages/parent/ChildProfile.vue'),
  },
```

- [ ] **Step 3: i18n** — `en.json` additions:

```json
  "parent": {
    "myChildren": "My Children",
    "noChildren": "No students linked to your account yet.",
    "grade": "Grade",
    "academicYear": "Academic Year",
    "homeroom": "Homeroom",
    "dateOfBirth": "Date of Birth",
    "nationality": "Nationality",
    "bloodGroup": "Blood Group",
    "medical": "Medical Conditions",
    "emergencyContact": "Emergency Contact",
    "emergencyPhone": "Emergency Phone"
  }
```

`ar.json` additions:

```json
  "parent": {
    "myChildren": "أبنائي",
    "noChildren": "لا يوجد طلاب مرتبطون بحسابك بعد.",
    "grade": "الصف",
    "academicYear": "العام الدراسي",
    "homeroom": "الفصل",
    "dateOfBirth": "تاريخ الميلاد",
    "nationality": "الجنسية",
    "bloodGroup": "فصيلة الدم",
    "medical": "الحالات الصحية",
    "emergencyContact": "جهة اتصال الطوارئ",
    "emergencyPhone": "هاتف الطوارئ"
  }
```

- [ ] **Step 4: Verify** — `npm test`, `npm run build`; manual smoke as guardian (link a Guardian with `user` to a test login, link to a student; view children + profile at `/portal`). Stop bench after; note what was manually verified.
- [ ] **Step 5: Commit** — `feat: parent portal pages (children overview and child profile)`

---

### Task 10: Provisioning seeds grades + Phase 1 wrap-up

**Files:**
- Modify: `ops/provision_school.py`, `ops/tests/test_provision_school.py`
- Modify: `README.md`

- [ ] **Step 1: Failing test** — add to `ops/tests/test_provision_school.py`:

```python
def test_seeds_default_grades_after_app_install():
    cmds = build_commands(make_config())
    flat = [" ".join(c) for c in cmds]
    seed_index = next(
        i
        for i, c in enumerate(flat)
        if "education_k12.k12_sis.grades.create_default_grade_programs" in c
    )
    last_install_index = max(i for i, c in enumerate(flat) if "install-app" in c)
    assert seed_index > last_install_index
```

Run (WSL `python3.11 -m pytest ops/tests -v`) → FAIL (StopIteration). Record.

- [ ] **Step 2: Implement** — in `build_commands`, after the install-app loop (before the set-config/set-value tail), add:

```python
    cmds.append(
        [
            "bench", *site, "execute",
            "education_k12.k12_sis.grades.create_default_grade_programs",
        ]
    )
```

Run → all ops tests pass (now 7).

- [ ] **Step 3: Full verification suite**

- Backend: `bench --site dev.localhost run-tests --app education_k12` → all modules (K12 Settings + 5 SIS test modules + promotion) pass.
- Ops: 7 passed. Frontend: `npm test` → 6 passed; `npm run build` OK.

- [ ] **Step 4: README** — add a short "Phase 1 (Core SIS)" subsection under the project intro: grade catalogue + seeding command, homeroom setup (Instructor.user custom field requirement for teacher portal access, Guardian.user for parents), promotion tool location in Desk, portal pages overview. Keep it to ~20 lines; link the Phase 1 plan doc.

- [ ] **Step 5: Commit + push + CI green**

```
git add -A
git commit -m "feat: provision grades on new sites; Phase 1 docs"
git push
```

Poll CI → all 3 jobs green.

---

## Self-review checklist (run after writing, before execution)

1. Spec coverage: grade levels ✔ (T1), sections/homerooms ✔ (T4), Gulf fields ✔ (T2), sibling linking ✔ (T3), document checklist ✔ (T5), promotion tool ✔ (T6), parent portal slice ✔ (T7+T9), teacher portal slice ✔ (T7+T8).
2. Type consistency: field/endpoint names match across tasks (`is_homeroom`, `homeroom_teacher`, `Instructor.user`, `education_k12.api.portal.*`, route names `TeacherHomerooms`/`HomeroomRoster`/`Children`/`ChildProfile`).
3. Every code step shows complete code; expected test counts stated per task.
