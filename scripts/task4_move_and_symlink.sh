#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

echo "=== Step 1: No .git to remove (--no-git was used) - verifying ==="
ls ~/frappe-bench-dev/apps/education_k12/.git 2>&1 || echo "No .git directory (expected - --no-git was used)"

echo ""
echo "=== Step 2: Creating monorepo apps directory ==="
mkdir -p /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps
echo "Directory created/verified"

echo ""
echo "=== Step 3: Moving app to monorepo ==="
mv ~/frappe-bench-dev/apps/education_k12 /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps/education_k12
echo "Move exit code: $?"

echo ""
echo "=== Step 4: Creating symlink ==="
ln -s /mnt/c/Users/asifm/source/repos/frappe-education-k12/apps/education_k12 ~/frappe-bench-dev/apps/education_k12
echo "Symlink exit code: $?"

echo ""
echo "=== Step 5: Verify symlink ==="
ls -la ~/frappe-bench-dev/apps/ | grep education_k12

echo ""
echo "=== Step 6: Check symlink target ==="
readlink ~/frappe-bench-dev/apps/education_k12
