#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd ~/frappe-bench-dev

echo "=== Installing education_k12 on dev.localhost ==="
bench --site dev.localhost install-app education_k12 2>&1
echo "Install exit code: $?"

echo ""
echo "=== Listing installed apps on dev.localhost ==="
bench --site dev.localhost list-apps 2>&1
