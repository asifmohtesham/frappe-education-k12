#!/bin/bash
# Clear the Windows paths to avoid parentheses issues
export PATH=/home/asif/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd ~/frappe-bench-dev && bench new-app --help 2>&1
