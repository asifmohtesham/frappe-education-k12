# K-12 Education SaaS on Frappe Education

Multi-school K-12 management platform for the Gulf market. Custom Frappe app
(`education_k12`) on top of unmodified upstream `frappe/education`.
Site-per-school tenancy; Frappe Desk for admins; Vue 3 + Frappe UI portal for
teachers and parents.

- **Design spec:** `docs/superpowers/specs/2026-06-12-k12-education-saas-design.md`
- **Current plan:** `docs/superpowers/plans/2026-06-12-phase-0-foundation.md`

## Layout

| Path | Purpose |
|---|---|
| `apps/education_k12/` | The Frappe app (backend + embedded portal SPA in `frontend/`) |
| `ops/` | Provisioning and fleet scripts |
| `docs/` | Specs and implementation plans |

## Development setup

See "Environment notes" in the Phase 0 plan. Short version: WSL2 Ubuntu,
`bench init` a v15 bench at `~/frappe-bench`, clone this repo to
`~/frappe-education-k12`, symlink `apps/education_k12` into the bench.
