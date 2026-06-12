# Phase 2 — Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The school-transport module: vehicles with drivers/attendants, routes with ordered stops, student route assignments with capacity enforcement, printable route manifests, transport fees structurally ready for Phase 3, and the parent portal showing each child's route/stop.

**Architecture:** Net-new doctypes (no upstream equivalent) in the `Education K12` module, business logic in a new `k12_transport/` package mirroring `k12_sis/`. The route's `standard_fee` Currency field is the hook Phase 3 fee structures will consume. Portal extension rides the existing `api/portal.py` authorization model.

**Tech Stack:** Frappe v15, Python 3.11, FrappeTestCase; Vue 3 + frappe-ui (one page extended).

**Spec:** `docs/superpowers/specs/2026-06-12-k12-education-saas-design.md` (Phase 2 section). GPS tracking explicitly out of scope.

---

## Environment (unchanged from Phase 1 — see README)

- Repo (Windows): `C:\Users\asifm\source\repos\frappe-education-k12`; bench (WSL): `~/frappe-bench-dev`, site `dev.localhost`, port 8002. NEVER touch `~/frappe-bench`.
- WSL invoke: `wsl -d Ubuntu -- bash -lc "export PATH=$HOME/.local/bin:$PATH; cd ~/frappe-bench-dev && <cmd>"`. Redis first. Migrate after doctype changes.
- Backend tests: `bench --site dev.localhost run-tests --app education_k12` (25 today). Frontend: npm on Windows (6 tests). Ops: 7.
- Commit trailer: blank line + `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## Naming & structure decisions

- Doctypes (module `Education K12`): `K12 Transport Staff`, `K12 Vehicle`, `K12 Transport Route`, `K12 Route Stop` (child), `K12 Transport Assignment`.
- Logic package: `apps/education_k12/education_k12/k12_transport/` (`__init__.py`, `manifest.py`, `tests/`).
- Permissions on all transport doctypes: Education Manager full; Academics User read/write/create (submit n/a — none are submittable).
- Assignment→stop reference is by `stop_name` (child rows can't be Link targets); validated against the route's stops.
- One ACTIVE assignment per (student, academic_year); vehicle capacity enforced per (route, academic_year) on active assignments.

## File map

```
apps/education_k12/education_k12/
├── k12_transport/
│   ├── __init__.py
│   ├── manifest.py                       # get_route_manifest (T4)
│   └── tests/ __init__.py, utils.py, test_vehicle.py, test_route.py,
│              test_assignment.py, test_manifest.py
├── api/portal.py                          # + transport in get_child_profile (T5)
├── k12_sis/tests/test_portal_api.py       # + 1 transport test (T5)
└── education_k12/
    ├── doctype/
    │   ├── k12_transport_staff/           # T1
    │   ├── k12_vehicle/                   # T1
    │   ├── k12_route_stop/                # T2 (child)
    │   ├── k12_transport_route/           # T2
    │   └── k12_transport_assignment/      # T3
    └── report/route_manifest/             # T4 (script report)

apps/education_k12/frontend/src/
├── pages/parent/ChildProfile.vue          # + transport rows (T5)
└── i18n/locales/en.json, ar.json          # + parent transport keys (T5)

README.md                                  # Phase 2 section (T6)
```

All doctype folders follow the existing pattern (`__init__.py`, `<name>.json`, `<name>.py`); controllers with no logic are `class X(Document): pass`.

---

### Task 1: K12 Transport Staff + K12 Vehicle

**Files:**
- Create: `k12_transport/__init__.py`, `k12_transport/tests/__init__.py` (empty)
- Create: `k12_transport/tests/utils.py`
- Create doctypes: `education_k12/doctype/k12_transport_staff/`, `education_k12/doctype/k12_vehicle/`
- Test: `k12_transport/tests/test_vehicle.py`

- [ ] **Step 1: Write the failing tests** — `k12_transport/tests/utils.py` first (shared by all transport tests):

```python
import frappe


def ensure_staff(name, role="Driver"):
    existing = frappe.db.get_value(
        "K12 Transport Staff", {"staff_name": name, "role": role}
    )
    if existing:
        return existing
    return (
        frappe.get_doc(
            {"doctype": "K12 Transport Staff", "staff_name": name, "role": role}
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_vehicle(vehicle_number, capacity=4, **extra):
    if frappe.db.exists("K12 Vehicle", vehicle_number):
        return vehicle_number
    return (
        frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": vehicle_number,
                "capacity": capacity,
                **extra,
            }
        )
        .insert(ignore_permissions=True)
        .name
    )


def ensure_route(route_name, vehicle, stops=None, **extra):
    if frappe.db.exists("K12 Transport Route", route_name):
        return route_name
    doc = frappe.get_doc(
        {
            "doctype": "K12 Transport Route",
            "route_name": route_name,
            "vehicle": vehicle,
            **extra,
        }
    )
    for index, stop in enumerate(stops or [("Main Gate", "07:00:00")], start=1):
        stop_name, pickup_time = stop
        doc.append(
            "stops",
            {"stop_name": stop_name, "sequence": index, "pickup_time": pickup_time},
        )
    return doc.insert(ignore_permissions=True).name
```

`test_vehicle.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_transport.tests.utils import ensure_staff


class TestVehicle(FrappeTestCase):
    def test_vehicle_with_driver_and_attendant(self):
        driver = ensure_staff("Driver One", "Driver")
        attendant = ensure_staff("Attendant One", "Attendant")
        vehicle = frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": "DXB A 11111",
                "capacity": 30,
                "driver": driver,
                "attendant": attendant,
            }
        ).insert(ignore_permissions=True)
        self.assertEqual(vehicle.name, "DXB A 11111")

    def test_capacity_must_be_positive(self):
        vehicle = frappe.get_doc(
            {"doctype": "K12 Vehicle", "vehicle_number": "DXB A 22222", "capacity": 0}
        )
        with self.assertRaises(frappe.ValidationError):
            vehicle.insert(ignore_permissions=True)

    def test_driver_field_requires_driver_role(self):
        attendant = ensure_staff("Attendant Two", "Attendant")
        vehicle = frappe.get_doc(
            {
                "doctype": "K12 Vehicle",
                "vehicle_number": "DXB A 33333",
                "capacity": 20,
                "driver": attendant,
            }
        )
        with self.assertRaises(frappe.ValidationError):
            vehicle.insert(ignore_permissions=True)
```

- [ ] **Step 2:** run module `education_k12.k12_transport.tests.test_vehicle` → record ImportError/DoesNotExistError failure.

- [ ] **Step 3: Create the doctypes.**

`k12_transport_staff.json`:

```json
{
 "actions": [],
 "autoname": "format:K12-TS-{#####}",
 "creation": "2026-06-12 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["staff_name", "role", "phone", "employee", "license_number", "license_expiry", "active"],
 "fields": [
  {"fieldname": "staff_name", "fieldtype": "Data", "label": "Name", "reqd": 1, "in_list_view": 1},
  {"fieldname": "role", "fieldtype": "Select", "options": "Driver\nAttendant", "label": "Role", "reqd": 1, "in_list_view": 1},
  {"fieldname": "phone", "fieldtype": "Data", "label": "Phone"},
  {"fieldname": "employee", "fieldtype": "Link", "options": "Employee", "label": "Employee"},
  {"fieldname": "license_number", "fieldtype": "Data", "label": "License Number", "depends_on": "eval:doc.role=='Driver'"},
  {"fieldname": "license_expiry", "fieldtype": "Date", "label": "License Expiry", "depends_on": "eval:doc.role=='Driver'"},
  {"fieldname": "active", "fieldtype": "Check", "label": "Active", "default": "1"}
 ],
 "links": [],
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Transport Staff",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "share": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_vehicle.json`:

```json
{
 "actions": [],
 "autoname": "field:vehicle_number",
 "creation": "2026-06-12 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["vehicle_number", "capacity", "make_model", "driver", "attendant", "disabled"],
 "fields": [
  {"fieldname": "vehicle_number", "fieldtype": "Data", "label": "Vehicle / Plate Number", "reqd": 1, "unique": 1, "in_list_view": 1},
  {"fieldname": "capacity", "fieldtype": "Int", "label": "Seat Capacity", "reqd": 1, "in_list_view": 1},
  {"fieldname": "make_model", "fieldtype": "Data", "label": "Make / Model"},
  {"fieldname": "driver", "fieldtype": "Link", "options": "K12 Transport Staff", "label": "Driver", "in_list_view": 1},
  {"fieldname": "attendant", "fieldtype": "Link", "options": "K12 Transport Staff", "label": "Attendant"},
  {"fieldname": "disabled", "fieldtype": "Check", "label": "Disabled"}
 ],
 "links": [],
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Vehicle",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "share": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_transport_staff.py`: `class K12TransportStaff(Document): pass`

`k12_vehicle.py`:

```python
import frappe
from frappe import _
from frappe.model.document import Document


class K12Vehicle(Document):
    def validate(self):
        if (self.capacity or 0) <= 0:
            frappe.throw(_("Seat capacity must be a positive number"))
        self._validate_staff_role("driver", "Driver")
        self._validate_staff_role("attendant", "Attendant")

    def _validate_staff_role(self, fieldname, expected_role):
        staff = self.get(fieldname)
        if not staff:
            return
        role = frappe.db.get_value("K12 Transport Staff", staff, "role")
        if role != expected_role:
            frappe.throw(
                _("{0} must be a transport staff member with role {1}").format(
                    self.meta.get_label(fieldname), expected_role
                )
            )
```

- [ ] **Step 4:** migrate; module → 3 OK; full suite → 28 backend tests green.
- [ ] **Step 5: Commit** `feat: transport staff and vehicle doctypes` (stage the two doctype dirs + k12_transport package skeleton + utils + test). Push; CI green.

---

### Task 2: K12 Transport Route + K12 Route Stop

**Files:**
- Create doctypes: `education_k12/doctype/k12_route_stop/` (child), `education_k12/doctype/k12_transport_route/`
- Test: `k12_transport/tests/test_route.py`

- [ ] **Step 1: failing tests** — `test_route.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_transport.tests.utils import ensure_vehicle


def make_route(route_name, stops):
    doc = frappe.get_doc(
        {
            "doctype": "K12 Transport Route",
            "route_name": route_name,
            "vehicle": ensure_vehicle("DXB R 10001", capacity=40),
        }
    )
    for index, stop_name in enumerate(stops, start=1):
        doc.append("stops", {"stop_name": stop_name, "sequence": index})
    return doc


class TestRoute(FrappeTestCase):
    def test_route_saves_with_ordered_stops_and_fee(self):
        route = make_route("Route Marina", ["Marina Mall", "JBR Walk"])
        route.standard_fee = 1500
        route.insert(ignore_permissions=True)
        saved = frappe.get_doc("K12 Transport Route", "Route Marina")
        self.assertEqual([s.stop_name for s in saved.stops], ["Marina Mall", "JBR Walk"])
        self.assertEqual(saved.standard_fee, 1500)

    def test_route_requires_at_least_one_stop(self):
        route = make_route("Route Empty", [])
        with self.assertRaises(frappe.ValidationError):
            route.insert(ignore_permissions=True)

    def test_duplicate_stop_names_rejected(self):
        route = make_route("Route Dup", ["Same Stop", "Same Stop"])
        with self.assertRaises(frappe.ValidationError):
            route.insert(ignore_permissions=True)
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: Create doctypes.**

`k12_route_stop.json` (child):

```json
{
 "actions": [],
 "creation": "2026-06-12 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["stop_name", "sequence", "pickup_time", "drop_time"],
 "fields": [
  {"fieldname": "stop_name", "fieldtype": "Data", "label": "Stop", "reqd": 1, "in_list_view": 1},
  {"fieldname": "sequence", "fieldtype": "Int", "label": "Sequence", "reqd": 1, "in_list_view": 1},
  {"fieldname": "pickup_time", "fieldtype": "Time", "label": "Pickup Time", "in_list_view": 1},
  {"fieldname": "drop_time", "fieldtype": "Time", "label": "Drop Time", "in_list_view": 1}
 ],
 "istable": 1,
 "links": [],
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Route Stop",
 "owner": "Administrator",
 "permissions": [],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_transport_route.json`:

```json
{
 "actions": [],
 "autoname": "field:route_name",
 "creation": "2026-06-12 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["route_name", "vehicle", "standard_fee", "disabled", "stops"],
 "fields": [
  {"fieldname": "route_name", "fieldtype": "Data", "label": "Route Name", "reqd": 1, "unique": 1, "in_list_view": 1},
  {"fieldname": "vehicle", "fieldtype": "Link", "options": "K12 Vehicle", "label": "Vehicle", "reqd": 1, "in_list_view": 1},
  {"fieldname": "standard_fee", "fieldtype": "Currency", "label": "Standard Termly Fee", "description": "Consumed by Fees module fee structures (Phase 3)"},
  {"fieldname": "disabled", "fieldtype": "Check", "label": "Disabled"},
  {"fieldname": "stops", "fieldtype": "Table", "options": "K12 Route Stop", "label": "Stops"}
 ],
 "links": [],
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Transport Route",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "share": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_route_stop.py`: `class K12RouteStop(Document): pass`

`k12_transport_route.py`:

```python
import frappe
from frappe import _
from frappe.model.document import Document


class K12TransportRoute(Document):
    def validate(self):
        if not self.stops:
            frappe.throw(_("A route needs at least one stop"))
        seen = set()
        for stop in self.stops:
            if stop.stop_name in seen:
                frappe.throw(_("Duplicate stop: {0}").format(stop.stop_name))
            seen.add(stop.stop_name)
```

- [ ] **Step 4:** migrate; module → 3 OK; full suite → 31 green.
- [ ] **Step 5: Commit** `feat: transport routes with ordered stops`. Push; CI green.

---

### Task 3: K12 Transport Assignment with capacity enforcement

**Files:**
- Create doctype: `education_k12/doctype/k12_transport_assignment/`
- Test: `k12_transport/tests/test_assignment.py`

- [ ] **Step 1: failing tests** — `test_assignment.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student
from education_k12.k12_transport.tests.utils import ensure_route, ensure_vehicle


def assign(student, route, stop_name="Main Gate", **extra):
    return frappe.get_doc(
        {
            "doctype": "K12 Transport Assignment",
            "student": student,
            "academic_year": ensure_academic_year(),
            "route": route,
            "stop_name": stop_name,
            **extra,
        }
    )


class TestTransportAssignment(FrappeTestCase):
    def setUp(self):
        self.route = ensure_route(
            "Route Assign", ensure_vehicle("DXB T 20001", capacity=2)
        )

    def test_assignment_saves_for_valid_stop(self):
        student = ensure_student("Bus Kid One")
        doc = assign(student, self.route)
        doc.insert(ignore_permissions=True)
        self.assertEqual(
            frappe.db.get_value("K12 Transport Assignment", doc.name, "stop_name"),
            "Main Gate",
        )

    def test_unknown_stop_rejected(self):
        student = ensure_student("Bus Kid Two")
        doc = assign(student, self.route, stop_name="Nowhere")
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)

    def test_one_active_assignment_per_student_per_year(self):
        student = ensure_student("Bus Kid Three")
        assign(student, self.route).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            assign(student, self.route).insert(ignore_permissions=True)

    def test_inactive_assignment_does_not_block_new_one(self):
        student = ensure_student("Bus Kid Four")
        first = assign(student, self.route)
        first.insert(ignore_permissions=True)
        first.active = 0
        first.save(ignore_permissions=True)
        assign(student, self.route).insert(ignore_permissions=True)  # must not raise

    def test_capacity_enforced(self):
        for index in range(2):  # vehicle capacity is 2
            assign(
                ensure_student(f"Bus Capacity Kid {index}"), self.route
            ).insert(ignore_permissions=True)
        with self.assertRaises(frappe.ValidationError):
            assign(ensure_student("Bus Capacity Kid Overflow"), self.route).insert(
                ignore_permissions=True
            )
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: Create doctype.**

`k12_transport_assignment.json`:

```json
{
 "actions": [],
 "autoname": "format:K12-TA-{#####}",
 "creation": "2026-06-12 16:00:00.000000",
 "doctype": "DocType",
 "engine": "InnoDB",
 "field_order": ["student", "student_name", "academic_year", "route", "stop_name", "direction", "active"],
 "fields": [
  {"fieldname": "student", "fieldtype": "Link", "options": "Student", "label": "Student", "reqd": 1, "in_list_view": 1},
  {"fieldname": "student_name", "fieldtype": "Data", "label": "Student Name", "fetch_from": "student.student_name", "in_list_view": 1},
  {"fieldname": "academic_year", "fieldtype": "Link", "options": "Academic Year", "label": "Academic Year", "reqd": 1},
  {"fieldname": "route", "fieldtype": "Link", "options": "K12 Transport Route", "label": "Route", "reqd": 1, "in_list_view": 1},
  {"fieldname": "stop_name", "fieldtype": "Data", "label": "Stop", "reqd": 1, "in_list_view": 1},
  {"fieldname": "direction", "fieldtype": "Select", "options": "Both\nPickup Only\nDrop Only", "default": "Both", "label": "Direction"},
  {"fieldname": "active", "fieldtype": "Check", "label": "Active", "default": "1"}
 ],
 "links": [],
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "K12 Transport Assignment",
 "owner": "Administrator",
 "permissions": [
  {"role": "Education Manager", "read": 1, "write": 1, "create": 1, "delete": 1, "email": 1, "print": 1, "share": 1},
  {"role": "Academics User", "read": 1, "write": 1, "create": 1, "email": 1, "print": 1, "share": 1}
 ],
 "sort_field": "modified",
 "sort_order": "DESC",
 "states": []
}
```

`k12_transport_assignment.py`:

```python
import frappe
from frappe import _
from frappe.model.document import Document


class K12TransportAssignment(Document):
    def validate(self):
        self.validate_stop_on_route()
        if self.active:
            self.validate_single_active_assignment()
            self.validate_vehicle_capacity()

    def validate_stop_on_route(self):
        stops = frappe.get_all(
            "K12 Route Stop",
            filters={"parent": self.route, "parenttype": "K12 Transport Route"},
            pluck="stop_name",
        )
        if self.stop_name not in stops:
            frappe.throw(
                _("Stop {0} is not on route {1}").format(self.stop_name, self.route)
            )

    def validate_single_active_assignment(self):
        existing = frappe.db.exists(
            "K12 Transport Assignment",
            {
                "student": self.student,
                "academic_year": self.academic_year,
                "active": 1,
                "name": ("!=", self.name),
            },
        )
        if existing:
            frappe.throw(
                _("{0} already has an active transport assignment for {1}").format(
                    self.student_name or self.student, self.academic_year
                )
            )

    def validate_vehicle_capacity(self):
        capacity = frappe.db.get_value(
            "K12 Vehicle",
            frappe.db.get_value("K12 Transport Route", self.route, "vehicle"),
            "capacity",
        )
        occupied = frappe.db.count(
            "K12 Transport Assignment",
            {
                "route": self.route,
                "academic_year": self.academic_year,
                "active": 1,
                "name": ("!=", self.name),
            },
        )
        if occupied >= (capacity or 0):
            frappe.throw(
                _("Route {0} is full ({1} seats)").format(self.route, capacity)
            )
```

- [ ] **Step 4:** migrate; module → 5 OK; full suite → 36 green.
- [ ] **Step 5: Commit** `feat: student transport assignments with capacity enforcement`. Push; CI green.

---

### Task 4: Route manifest (function + script report)

**Files:**
- Create: `k12_transport/manifest.py`
- Create report: `education_k12/report/route_manifest/` (`__init__.py`, `route_manifest.json`, `route_manifest.py`)
- Test: `k12_transport/tests/test_manifest.py`

- [ ] **Step 1: failing tests** — `test_manifest.py`:

```python
import frappe
from frappe.tests.utils import FrappeTestCase

from education_k12.k12_sis.tests.utils import ensure_academic_year, ensure_student
from education_k12.k12_transport.manifest import get_route_manifest
from education_k12.k12_transport.tests.utils import (
    ensure_route,
    ensure_staff,
    ensure_vehicle,
)


class TestRouteManifest(FrappeTestCase):
    def setUp(self):
        self.year = ensure_academic_year()
        driver = ensure_staff("Manifest Driver", "Driver")
        vehicle = ensure_vehicle("DXB M 30001", capacity=10, driver=driver)
        self.route = ensure_route(
            "Route Manifest",
            vehicle,
            stops=[("Stop A", "07:00:00"), ("Stop B", "07:15:00")],
        )

    def _assign(self, student_name, stop_name):
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": ensure_student(student_name),
                "academic_year": self.year,
                "route": self.route,
                "stop_name": stop_name,
            }
        ).insert(ignore_permissions=True)

    def test_manifest_groups_students_by_stop_in_sequence(self):
        self._assign("Manifest Kid B", "Stop B")
        self._assign("Manifest Kid A", "Stop A")
        manifest = get_route_manifest(self.route, self.year)

        self.assertEqual(manifest["route"], self.route)
        self.assertEqual(manifest["vehicle"]["vehicle_number"], "DXB M 30001")
        self.assertEqual(manifest["vehicle"]["driver_name"], "Manifest Driver")
        self.assertEqual([s["stop_name"] for s in manifest["stops"]], ["Stop A", "Stop B"])
        self.assertEqual(len(manifest["stops"][0]["students"]), 1)
        self.assertEqual(len(manifest["stops"][1]["students"]), 1)

    def test_inactive_assignments_excluded(self):
        self._assign("Manifest Kid C", "Stop A")
        assignment = frappe.get_all(
            "K12 Transport Assignment",
            filters={"route": self.route, "academic_year": self.year},
            pluck="name",
        )[0]
        doc = frappe.get_doc("K12 Transport Assignment", assignment)
        doc.active = 0
        doc.save(ignore_permissions=True)

        manifest = get_route_manifest(self.route, self.year)
        total = sum(len(s["students"]) for s in manifest["stops"])
        self.assertEqual(total, 0)

    def test_empty_stops_still_listed(self):
        manifest = get_route_manifest(self.route, self.year)
        self.assertEqual(len(manifest["stops"]), 2)
        self.assertTrue(all(s["students"] == [] for s in manifest["stops"]))
```

- [ ] **Step 2:** run module → record failure.

- [ ] **Step 3: Implement** — `k12_transport/manifest.py`:

```python
"""Printable route manifests: who boards where, per route and year."""

import frappe


def get_route_manifest(route, academic_year):
    route_doc = frappe.get_doc("K12 Transport Route", route)
    vehicle = frappe.db.get_value(
        "K12 Vehicle",
        route_doc.vehicle,
        ["vehicle_number", "capacity", "driver", "attendant"],
        as_dict=True,
    )
    vehicle["driver_name"] = (
        frappe.db.get_value("K12 Transport Staff", vehicle.driver, "staff_name")
        if vehicle.driver
        else None
    )
    vehicle["attendant_name"] = (
        frappe.db.get_value("K12 Transport Staff", vehicle.attendant, "staff_name")
        if vehicle.attendant
        else None
    )

    assignments = frappe.get_all(
        "K12 Transport Assignment",
        filters={"route": route, "academic_year": academic_year, "active": 1},
        fields=["student", "student_name", "stop_name", "direction"],
        order_by="student_name asc",
    )
    by_stop = {}
    for assignment in assignments:
        by_stop.setdefault(assignment.stop_name, []).append(assignment)

    stops = [
        {
            "stop_name": stop.stop_name,
            "sequence": stop.sequence,
            "pickup_time": stop.pickup_time,
            "drop_time": stop.drop_time,
            "students": by_stop.get(stop.stop_name, []),
        }
        for stop in sorted(route_doc.stops, key=lambda s: s.sequence)
    ]

    return {
        "route": route_doc.name,
        "academic_year": academic_year,
        "vehicle": vehicle,
        "stops": stops,
    }
```

`report/route_manifest/route_manifest.json`:

```json
{
 "add_total_row": 0,
 "columns": [],
 "creation": "2026-06-12 16:00:00.000000",
 "disabled": 0,
 "docstatus": 0,
 "doctype": "Report",
 "filters": [],
 "is_standard": "Yes",
 "letterhead": null,
 "modified": "2026-06-12 16:00:00.000000",
 "modified_by": "Administrator",
 "module": "Education K12",
 "name": "Route Manifest",
 "owner": "Administrator",
 "prepared_report": 0,
 "ref_doctype": "K12 Transport Assignment",
 "report_name": "Route Manifest",
 "report_type": "Script Report",
 "roles": [
  {"role": "Education Manager"},
  {"role": "Academics User"}
 ]
}
```

`report/route_manifest/route_manifest.py`:

```python
import frappe
from frappe import _

from education_k12.k12_transport.manifest import get_route_manifest


def execute(filters=None):
    filters = filters or {}
    columns = [
        {"label": _("Stop"), "fieldname": "stop_name", "fieldtype": "Data", "width": 180},
        {"label": _("Pickup"), "fieldname": "pickup_time", "fieldtype": "Data", "width": 100},
        {"label": _("Student"), "fieldname": "student", "fieldtype": "Link", "options": "Student", "width": 160},
        {"label": _("Student Name"), "fieldname": "student_name", "fieldtype": "Data", "width": 200},
        {"label": _("Direction"), "fieldname": "direction", "fieldtype": "Data", "width": 110},
    ]
    if not (filters.get("route") and filters.get("academic_year")):
        return columns, []

    manifest = get_route_manifest(filters["route"], filters["academic_year"])
    rows = []
    for stop in manifest["stops"]:
        for student in stop["students"]:
            rows.append(
                {
                    "stop_name": stop["stop_name"],
                    "pickup_time": str(stop["pickup_time"] or ""),
                    "student": student.student,
                    "student_name": student.student_name,
                    "direction": student.direction,
                }
            )
    return columns, rows
```

Also create `report/__init__.py` and `report/route_manifest/__init__.py` (empty) if missing. The report needs filters defined client-side: create `report/route_manifest/route_manifest.js`:

```javascript
frappe.query_reports["Route Manifest"] = {
	filters: [
		{
			fieldname: "route",
			label: __("Route"),
			fieldtype: "Link",
			options: "K12 Transport Route",
			reqd: 1,
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
		},
	],
};
```

- [ ] **Step 4:** migrate; module → 3 OK; full suite → 39 green. Sanity-check the report loads: `bench --site dev.localhost execute frappe.client.get_list --kwargs "{'doctype':'Report','filters':{'name':'Route Manifest'},'limit_page_length':1}"` returns the report after migrate.
- [ ] **Step 5: Commit** `feat: route manifest function and script report`. Push; CI green.

---

### Task 5: Parent portal shows child's transport

**Files:**
- Modify: `api/portal.py` (transport in get_child_profile)
- Modify: `k12_sis/tests/test_portal_api.py` (+1 test)
- Modify: `frontend/src/pages/parent/ChildProfile.vue`, `frontend/src/i18n/locales/en.json`, `ar.json`

- [ ] **Step 1: failing backend test** — append to `TestPortalAPI` in `test_portal_api.py`:

```python
    def test_child_profile_includes_transport(self):
        from education_k12.k12_transport.tests.utils import ensure_route, ensure_vehicle

        child = ensure_student("Portal Bus Child")
        user = ensure_user("parent.bus@test.k12.local", "Parent Bus", roles=("Guardian",))
        link_guardian_to_student(child, ensure_guardian("Parent Bus", user))
        route = ensure_route(
            "Route Portal", ensure_vehicle("DXB P 40001", capacity=10)
        )
        frappe.get_doc(
            {
                "doctype": "K12 Transport Assignment",
                "student": child,
                "academic_year": ensure_academic_year(),
                "route": route,
                "stop_name": "Main Gate",
            }
        ).insert(ignore_permissions=True)

        frappe.set_user(user)
        profile = portal.get_child_profile(child)
        self.assertEqual(profile["transport"]["route"], route)
        self.assertEqual(profile["transport"]["stop"], "Main Gate")

        child_no_bus = ensure_student("Portal Walk Child")
        frappe.set_user("Administrator")
        link_guardian_to_student(
            child_no_bus, frappe.db.get_value("Guardian", {"user": user})
        )
        frappe.set_user(user)
        self.assertIsNone(portal.get_child_profile(child_no_bus)["transport"])
```

Run module → FAIL (KeyError "transport"). Record.

- [ ] **Step 2: implement** — in `api/portal.py`, add to `get_child_profile` before `return profile`:

```python
    profile["transport"] = _transport_for(student)
```

and the helper:

```python
def _transport_for(student):
    assignment = frappe.db.get_value(
        "K12 Transport Assignment",
        {"student": student, "active": 1},
        ["route", "stop_name", "direction"],
        as_dict=True,
    )
    if not assignment:
        return None
    stop = (
        frappe.db.get_value(
            "K12 Route Stop",
            {
                "parent": assignment.route,
                "parenttype": "K12 Transport Route",
                "stop_name": assignment.stop_name,
            },
            ["pickup_time", "drop_time"],
            as_dict=True,
        )
        or frappe._dict()
    )
    return {
        "route": assignment.route,
        "stop": assignment.stop_name,
        "direction": assignment.direction,
        "pickup_time": str(stop.pickup_time) if stop.get("pickup_time") else None,
        "drop_time": str(stop.drop_time) if stop.get("drop_time") else None,
    }
```

Run module → 8 OK; full suite → 40 green.

- [ ] **Step 3: frontend** — in `ChildProfile.vue`, append to `profileFields`:

```js
  { key: 'busRoute', label: 'parent.busRoute', value: () => profile.data?.transport?.route },
  { key: 'busStop', label: 'parent.busStop', value: () => profile.data?.transport?.stop },
  { key: 'busPickup', label: 'parent.busPickup', value: () => profile.data?.transport?.pickup_time },
```

i18n `en.json` parent additions: `"busRoute": "Bus Route"`, `"busStop": "Bus Stop"`, `"busPickup": "Pickup Time"`.
`ar.json`: `"busRoute": "خط الحافلة"`, `"busStop": "موقف الحافلة"`, `"busPickup": "وقت الصعود"`.

`npm test` (6 pass), `npm run build` OK.

- [ ] **Step 4: Commit** `feat: child transport details in parent portal`. Push; CI green.

---

### Task 6: Phase 2 wrap-up

**Files:**
- Modify: `README.md`

- [ ] **Step 1: full verification suite** — backend (`run-tests --app education_k12`) → 40 OK; ops 7; frontend 6; `npm run build` OK.
- [ ] **Step 2: README** — add "Phase 2 (Transport)" subsection (~15 lines): doctypes overview (staff/vehicle/route/stops/assignment), capacity + one-active-assignment rules, Route Manifest report (Desk → Report), `standard_fee` on routes as the Phase 3 hook, parent portal transport display. Update backend test count to 40. Link this plan doc.
- [ ] **Step 3: Commit** `docs: Phase 2 transport documentation` + push + CI green.

---

## Self-review checklist

1. Spec coverage: Vehicle ✔ (T1), Route/Stop ✔ (T2), Route Assignment ✔ (T3), driver/attendant records ✔ (T1), route manifests ✔ (T4), transport fee items for Phase 3 ✔ (standard_fee, T2), parent portal route/stop ✔ (T5). GPS excluded ✔.
2. Name consistency: doctype names, `stop_name` reference, `standard_fee`, portal `transport` dict keys match between API (T5 backend) and ChildProfile.vue (T5 frontend).
3. Test count math: 25 + 3 + 3 + 5 + 3 + 1 = 40 backend.
