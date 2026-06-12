#!/bin/bash
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd ~/frappe-bench-dev

echo "=== Running bench new-app with piped answers ==="
# Prompt order (based on typical frappe bench new-app):
# 1. App Title
# 2. App Description
# 3. App Publisher
# 4. App Email
# 5. App License (mit)
# 6. Create GitHub Workflow? (n)

printf 'Education K12\nK-12 extensions for Frappe Education\nAsif Mohtesham\nasifmohtesham@gmail.com\nmit\nn\n' | bench new-app --no-git education_k12 2>&1
echo ""
echo "=== Exit code: $? ==="
