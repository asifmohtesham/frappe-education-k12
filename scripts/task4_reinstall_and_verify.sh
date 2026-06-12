#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "=== Reinstalling editable package with new path (via symlink) ==="
~/frappe-bench-dev/env/bin/pip install --quiet -e ~/frappe-bench-dev/apps/education_k12 2>&1
echo "pip install exit code: $?"

echo ""
echo "=== pip show education_k12 after reinstall ==="
~/frappe-bench-dev/env/bin/pip show education_k12 2>&1

echo ""
echo "=== Verify modules.txt in monorepo ==="
cat /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps/education_k12/education_k12/modules.txt

echo ""
echo "=== Verify monorepo app directory listing ==="
ls /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps/education_k12/
