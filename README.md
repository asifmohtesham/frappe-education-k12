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

### Host requirements

- Windows 11 with WSL2 running Ubuntu (20.04 or later). Python 3.11 is required
  inside WSL for the bench virtualenv — on Ubuntu 20.04 install it manually
  (`sudo apt install python3.11 python3.11-venv`).
- Node 20 on **Windows** (not in WSL). No yarn; npm only.

### App stack

Per [`docs/decisions/0001-erpnext-dependency.md`](docs/decisions/0001-erpnext-dependency.md),
`frappe/education` requires ERPNext. Install order for every site:

```
frappe (version-15) → erpnext (version-15) → education (version-15.2) → education_k12
```

Note: the upstream `frappe/education` repository has no `version-15` branch;
use `version-15.2`.

### Bench setup (WSL)

These steps use `~/frappe-bench-dev` as the bench path. On a fresh machine any
path works; the `-dev` suffix here avoids clashing with a pre-existing bench.
Default Frappe web port is 8000; the instructions below use **8002** for the
same reason — omit the `webserver_port` override on a fresh machine.

```bash
# Install bench CLI (inside WSL)
pip3 install frappe-bench          # bench ~5.16

# Initialise bench with Frappe v15
bench init ~/frappe-bench-dev --frappe-branch version-15 \
    --python python3.11

cd ~/frappe-bench-dev

# (Optional) avoid port clash if another bench is already on 8000
bench set-config -g webserver_port 8002

# Get apps
bench get-app erpnext --branch version-15
bench get-app education https://github.com/frappe/education --branch version-15.2
```

### Symlink this repo into the bench (WSL)

The repo lives on the Windows filesystem; symlink the app folder into the bench
rather than cloning again:

```bash
ln -s /mnt/c/Users/<you>/source/repos/frappe-education-k12/apps/education_k12 \
    ~/frappe-bench-dev/apps/education_k12

~/frappe-bench-dev/env/bin/pip install -e ~/frappe-bench-dev/apps/education_k12

# Register the app so bench tracks it
echo "education_k12" >> ~/frappe-bench-dev/sites/apps.txt
```

### Create the dev site (WSL)

```bash
# Redis must be running before bench site commands
redis-cli ping || redis-server --daemonize yes

cd ~/frappe-bench-dev

bench new-site dev.localhost \
    --admin-password admin \
    --db-root-password <mariadb-root-password>

bench --site dev.localhost set-config developer_mode 1
bench --site dev.localhost set-config allow_tests true

# Install apps in stack order
bench --site dev.localhost install-app erpnext
bench --site dev.localhost install-app education
bench --site dev.localhost install-app education_k12
```

Start the bench:

```bash
cd ~/frappe-bench-dev && bench start
```

Portal: `http://localhost:8002/portal` (log in with the `admin` credentials set
above, or any site user).

### Frontend tooling (Windows PowerShell)

```powershell
cd apps\education_k12\frontend

npm install          # first time only

npm run dev          # Vite dev server on :8080, proxies API to bench on :8002
npm run build        # production build → public/frontend/ + www/portal.html (both gitignored)
npm test             # Vitest unit tests
```

### Running the test suite

| Layer | Command | Where | Expected |
|---|---|---|---|
| Backend | `bench --site dev.localhost run-tests --app education_k12` | WSL `~/frappe-bench-dev` | 1 test OK |
| Ops | `python3.11 -m pytest ops/tests -v` | WSL, repo root | 6 passed |
| Frontend | `npm test` | Windows, `apps/education_k12/frontend` | 2 passed |

Redis must be up before the backend test command.

### Provisioning a school site

```bash
# from the bench directory in WSL, with redis running
python3.11 /mnt/c/Users/<you>/source/repos/frappe-education-k12/ops/provision_school.py \
  --site greenfield.localhost --school-name "Greenfield Academy" \
  --admin-password <admin-pw> --db-root-password <db-root-pw>
# optional: --default-language ar
```

### CI

Three GitHub Actions jobs run on every push to `master` and on pull requests
(`.github/workflows/ci.yml`): `backend-tests`, `frontend-tests`, `ops-tests`.
