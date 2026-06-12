#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
echo "=== Checking if education_k12 already exists in bench ==="
ls ~/frappe-bench-dev/apps/ 2>&1
echo ""
echo "=== Checking monorepo apps directory ==="
ls /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps/ 2>&1
echo ""
echo "=== Checking sites/apps.txt ==="
cat ~/frappe-bench-dev/sites/apps.txt 2>&1
