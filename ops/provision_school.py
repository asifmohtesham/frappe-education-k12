"""Provision a new school site on the bench.

First cut (Phase 0): create site, install apps, set the school display name.
Designed as importable functions so a future control-plane app can call
`provision()` directly; the CLI is a thin wrapper.

Run from the bench directory:
    python3.11 /path/to/ops/provision_school.py \
        --site alnoor.localhost --school-name "Al Noor International School" \
        --admin-password ... --db-root-password ...
"""

import argparse
import os
import subprocess
from dataclasses import dataclass

# App stack per docs/decisions/0001-erpnext-dependency.md
APPS = ("erpnext", "education", "education_k12")


@dataclass
class SchoolConfig:
    site_name: str
    school_name: str
    admin_password: str
    db_root_password: str
    default_language: str = "en"


def build_commands(cfg: SchoolConfig) -> list[list[str]]:
    """Return the ordered bench commands that provision a school site."""
    site = ["--site", cfg.site_name]
    cmds = [
        [
            "bench", "new-site", cfg.site_name,
            "--admin-password", cfg.admin_password,
            "--db-root-password", cfg.db_root_password,
        ]
    ]
    cmds += [["bench", *site, "install-app", app] for app in APPS]
    cmds.append(
        [
            "bench", *site, "execute",
            "education_k12.k12_sis.grades.create_default_grade_programs",
        ]
    )
    cmds.append(["bench", *site, "set-config", "lang", cfg.default_language])
    set_value_kwargs = repr(
        {
            "doctype": "K12 Settings",
            "name": "K12 Settings",
            "fieldname": "school_display_name",
            "value": cfg.school_name,
        }
    )
    cmds.append(
        [
            "bench", *site, "execute", "frappe.client.set_value",
            "--kwargs", set_value_kwargs,
        ]
    )
    return cmds


def _bench_env() -> dict:
    """Return an environment dict that ensures ~/.local/bin is on PATH."""
    env = os.environ.copy()
    local_bin = os.path.expanduser("~/.local/bin")
    if local_bin not in env.get("PATH", "").split(os.pathsep):
        env["PATH"] = local_bin + os.pathsep + env.get("PATH", "")
    return env


def provision(cfg: SchoolConfig, runner=subprocess.run) -> None:
    """Execute the provisioning commands; fails fast on the first error."""
    env = _bench_env()
    for cmd in build_commands(cfg):
        runner(cmd, check=True, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", required=True, dest="site_name")
    parser.add_argument("--school-name", required=True, dest="school_name")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--db-root-password", required=True)
    parser.add_argument("--default-language", default="en", choices=["en", "ar"])
    args = parser.parse_args()
    provision(SchoolConfig(**vars(args)))


if __name__ == "__main__":
    main()
