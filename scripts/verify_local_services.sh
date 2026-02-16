#!/bin/bash
# scripts/verify_local_services.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== HONGSTR Local Services Verification ==="

# 1. Check LaunchAgents plists in ~/Library
echo "[1/4] Checking LaunchAgents deployment..."
for label in realtime_ws daily_etl daily_healthcheck retention_cleanup; do
    plist="$HOME/Library/LaunchAgents/com.hongstr.$label.plist"
    if [ -f "$plist" ]; then
        echo "  [OK] $label.plist exists."
    else
        echo "  [FAIL] $label.plist missing."
    fi
done

# 2. Check launchctl status
echo -e "\n[2/4] Checking launchctl status..."
launchctl list | grep hongstr || echo "  [WARN] No hongstr jobs found in launchctl list."

# 3. Check Logs Activity
echo -e "\n[3/4] Checking most recent log entries..."
if [ -f "logs/realtime_ws.log" ]; then
    echo "  [realtime_ws.log] Last 2 lines:"
    tail -n 2 "logs/realtime_ws.log"
else
    echo "  [FAIL] logs/realtime_ws.log missing."
fi

# 4. Check Reporting
echo -e "\n[4/4] Checking healthcheck reports..."
if [ -f "data/reports/daily_backtest_health.csv" ]; then
    echo "  [OK] Health report exists. Recent results:"
    tail -n 3 "data/reports/daily_backtest_health.csv"
else
    echo "  [WARN] data/reports/daily_backtest_health.csv not found yet."
fi

echo -e "\nVerification Complete."
