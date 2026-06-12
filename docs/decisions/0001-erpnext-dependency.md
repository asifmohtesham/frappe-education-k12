# 0001 — Does frappe/education require ERPNext?

**Date:** 2026-06-12
**Checked on:** frappe/education branch version-15.2, commit 51aaa1d

## Findings

- `required_apps` in hooks.py: `["erpnext"]` (line 14 of `education/hooks.py`)
- Bare-site install result: When running `bench --site depcheck.localhost install-app education` on a site with only frappe, bench automatically pulled in erpnext first (logged "Installing erpnext..."), then installed education. Removing erpnext from the stack is not possible — bench enforces the declared dependency.
- Fees doctypes load without ERPNext: N/A — education cannot be installed without ERPNext. With both present, `frappe.db.exists("DocType", "Fees")` returned `"Fees"` confirming the Fees doctype is registered and accessible.

## Decision

ERPNext IS part of the per-site app stack.
App install order for all sites: frappe → erpnext → education → education_k12
