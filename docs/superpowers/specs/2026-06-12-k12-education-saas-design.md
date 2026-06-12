# K-12 Education SaaS on Frappe Education — Design

**Date:** 2026-06-12
**Status:** Approved

## Overview

A multi-school K-12 management platform for the Middle East/Gulf market, built as a
custom Frappe app (`education_k12`) layered on the unmodified upstream
`frappe/education` app. Each school runs on its own Frappe site (own database) on a
shared bench/cluster. School admins use Frappe Desk; teachers and parents use a
custom Vue 3 + Frappe UI portal. v1 onboarding is sales-led and script-driven
(hybrid model): provisioning is manual but fully automated by scripts designed so a
self-service signup layer can wrap them later without rework.

## Decisions (settled during brainstorming)

| Decision | Choice |
|---|---|
| Audience | Multi-school product/SaaS |
| v1 scope | Core SIS, Transport, Fees + Billing, Attendance + Timetable, Gradebook + Report cards |
| Tenancy | Site-per-school (Frappe native multi-site) |
| Codebase strategy | Custom app on top of unmodified upstream `frappe/education` |
| Frontend | Frappe Desk for admins; custom Vue 3 + Frappe UI portal for teachers and parents |
| Market | Middle East/Gulf (Arabic/RTL, VAT, Gulf curricula mix) |
| Onboarding | Hybrid: manual for v1 launch customers, scripts designed for future self-service wrapping |
| Build sequencing | Vertical slices, academic-year-aligned phase order |

## Architecture

### App stack (installed on every school site)

```
frappe → erpnext → education (upstream, untouched) → education_k12 (ours)
```

ERPNext provides the accounting backbone for fees. The exact dependency chain
(whether current `frappe/education` hard-requires ERPNext for the fees module) is
verified in Phase 0; if fees work without ERPNext we still install it for GL/VAT
reporting unless verification shows it is dead weight.

### Extension strategy

`education_k12` never patches upstream. It extends via:

- **New doctypes** for K-12-specific concepts (sections/homerooms, transport, report
  card templates, etc.)
- **Custom fields** on upstream doctypes, shipped as fixtures
- **Document-event hooks** (`doc_events` in `hooks.py`)
- **Controller overrides** (`override_doctype_class`) only where hooks are insufficient
- **Whitelisted REST APIs** consumed by the portal

### Repository layout

```
repo/
├── apps/education_k12/         # custom Frappe app
│   ├── education_k12/
│   │   ├── k12_sis/            # Phase 1
│   │   ├── k12_transport/      # Phase 2
│   │   ├── k12_fees/           # Phase 3
│   │   ├── k12_attendance/     # Phase 4
│   │   ├── k12_assessment/     # Phase 5
│   │   └── api/                # whitelisted portal endpoints
│   └── frontend/               # Vue 3 + Frappe UI portal SPA (Vite)
│       ├── src/teacher/
│       └── src/parent/
├── ops/                        # provisioning + fleet management
│   ├── provision_school.py
│   └── upgrade_fleet.py
└── docs/
```

### Portal

One SPA embedded in the app, served at `/portal`, role-based routing for Teacher and
Guardian roles. Auth rides Frappe's standard session. Internationalization (English +
Arabic) and RTL layout support from day one via vue-i18n aligned with Frappe's
translation system. Responsive web only — no native mobile apps in v1.

### Tenancy

One site = one school = one campus. Per-school configuration covers academic
calendar, grading scales, VAT rate, currency, locale, and branding. Strong data
isolation per tenant; per-site backups.

## Modules (build order = phase order)

### Phase 0 — Foundation

Bench setup, app scaffolding (`education_k12`), CI pipeline, verification of the
education/ERPNext dependency, portal SPA shell with auth and i18n/RTL plumbing, and a
first cut of `provision_school.py` good enough to spin up dev/test sites.

### Phase 1 — Core SIS

Upstream provides Student, Guardian, Program, Program Enrollment, Student Group,
Academic Year/Term, Student Applicant/Admission. The K-12 layer adds:

- Grade Level structure (KG1–Grade 12) mapped onto Programs
- Sections/homerooms (Student Group subtype) with homeroom teacher assignment
- Gulf-specific student fields: nationality, Emirates ID/Iqama, visa details,
  medical info, emergency contacts
- Sibling linking across students
- Admission document checklist
- Year-end bulk Promotion tool (grade → next grade, with per-student overrides)

Portal slice: parent sees children overview and profiles; teacher sees homeroom
roster and student profiles.

### Phase 2 — Transport

Net-new module (no upstream equivalent):

- Doctypes: Vehicle, Route, Stop, Route Assignment (student ↔ route/stop),
  Driver/Attendant records
- Route manifests (printable lists per vehicle/route)
- Transport fee items defined here, consumed by Phase 3 fee structures
- GPS tracking explicitly out of scope for v1

Portal slice: parent sees assigned route/stop per child.

### Phase 3 — Fees + Billing

On top of upstream fee doctypes:

- Fee structures with installment plans and sibling discounts
- Gulf VAT handling (5% UAE / 15% KSA — per-school configuration)
- Transport fees from Phase 2 included in fee structures
- Pluggable payment-gateway interface; first concrete gateway (Tap, PayTabs, or
  Stripe) selected and integrated during this phase
- Receipts and outstanding-fee reminder emails

Portal slice: parent views fee schedule and outstanding balance, pays online,
downloads receipts.

SaaS billing of the schools themselves stays manual in v1 (tracked internally).

### Phase 4 — Attendance + Timetable

- Homeroom daily attendance (KG/primary) and period-wise attendance (secondary) —
  granularity is a per-school setting
- Timetable builder per section on top of upstream Course Schedule
- Teacher substitution handling
- Guardian-submitted leave applications via portal
- Automatic absence-notification emails to parents

Portal slice: teacher takes attendance and views timetable; parent sees attendance
history and submits leave requests.

### Phase 5 — Gradebook + Report cards

- Configurable term structure and weighted assessment categories (homework,
  quizzes, exams) on top of upstream Assessment Plan/Result
- Configurable grading scales (letter, percentage, British/IB-friendly)
- KG skills/behavior rubrics
- Report card PDF templates per grade band with school branding

Portal slice: teacher gradebook entry screens; parent views/downloads report cards.

### Phase 6 — Ops hardening + pilot

- `provision_school.py` finalized: idempotent; creates site, installs apps, seeds
  fixtures (academic year, grading scales, roles, VAT config), creates admin user;
  parameterized by school name, domain, locale, calendar. Written as importable
  functions so a future control-plane app can call them.
- `upgrade_fleet.py`: staged rollout — canary site first, then fleet-wide
  `bench migrate`.
- Per-site backup schedule and basic monitoring.
- Onboard the first pilot school.

## Error handling & testing

- Frappe unit tests for every new doctype/controller
- Role-permission test matrix (Teacher/Guardian/Admin against each API)
- Integration tests for the risky flows: promotion, fee generation (incl. VAT and
  sibling discounts), report card generation
- Playwright e2e for the two money paths: attendance submission and online payment
  (gateway sandbox)
- CI: GitHub Actions running bench tests against MariaDB

## Out of scope for v1

- LMS/content delivery
- Self-service signup and automated SaaS subscription billing
- GPS bus tracking
- Native mobile apps (portal is responsive web)
- Multi-campus schools (one site = one campus)
