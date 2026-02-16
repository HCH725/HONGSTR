#!/bin/bash
# scripts/verify_local_services.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== HONGSTR Local Services Verification ==="

# 1. Check LaunchAgents plists in ~/Library
echo -e "\033[1;34m[1/4] Checking LaunchAgents deployment...\033[0m"
for label in realtime_ws daily_etl daily_healthcheck retention_cleanup; do
    plist="$HOME/Library/LaunchAgents/com.hongstr.$label.plist"
    if [ -f "$plist" ]; then
        echo "  [OK] $label.plist exists."
    else
        echo "  [FAIL] $label.plist missing."
    fi
done

# 2. Check launchctl status
echo -e "\n\033[1;34m[2/4] Checking launchctl status...\033[0m"
launchctl list | grep hongstr || echo "  [WARN] No hongstr jobs found in launchctl list."

# 3. Check Logs Activity
echo -e "\n\033[1;34m[3/4] Checking most recent log entries...\033[0m"
if [ -f "logs/realtime_ws.log" ]; then
    echo "  [realtime_ws.log] Last 2 lines:"
    tail -n 2 "logs/realtime_ws.log"
else
    echo "  [FAIL] logs/realtime_ws.log missing."
fi

# 4. Manual Dry-Run Verification
echo -e "\n\033[1;34m[4/4] Running manual dry-run checks...\033[0m"
echo "  [Retention] checking path safety..."
bash scripts/retention_cleanup.sh --dry_run | tail -n 5

echo -e "\n  [Healthcheck] verifying last report..."
if [ -f "data/reports/daily_backtest_health.csv" ]; then
    tail -n 3 "data/reports/daily_backtest_health.csv"
else
    echo "  [WARN] No health report yet. Run: bash scripts/daily_backtest_healthcheck.sh"
fi

echo -e "\n\033[1;32mVerification Complete.\033[0m"
