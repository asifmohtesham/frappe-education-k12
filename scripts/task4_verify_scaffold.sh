#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
echo "=== App directory contents ==="
ls ~/frappe-bench-dev/apps/education_k12/
echo ""
echo "=== modules.txt ==="
cat ~/frappe-bench-dev/apps/education_k12/education_k12/modules.txt 2>&1
echo ""
echo "=== pyproject.toml ==="
cat ~/frappe-bench-dev/apps/education_k12/pyproject.toml 2>&1
echo ""
echo "=== hooks.py (first 40 lines) ==="
head -40 ~/frappe-bench-dev/apps/education_k12/education_k12/hooks.py 2>&1
echo ""
echo "=== pip show education_k12 ==="
~/frappe-bench-dev/env/bin/pip show education_k12 2>&1
echo ""
echo "=== sites/apps.txt ==="
cat ~/frappe-bench-dev/sites/apps.txt 2>&1
