#!/usr/bin/env python3
"""
HONGSTR Brake Healthcheck (R3-C)
Verifies existence and recency of critical system artifacts (brakes).
Usage: ./scripts/brake_healthcheck.py
Env: BRAKE_HC_STRICT=1 (Exit 1 on any FAIL)
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
FRESHNESS_PATH = "data/state/freshness_table.json"
REGIME_PATH_CANDIDATES = (
    "reports/state_atomic/regime_monitor_latest.json",
    "data/state/regime_monitor_latest.json",
)
HEALTH_JSON_PATH = "reports/state_atomic/brake_health_latest.json"

FRESHNESS_MAX_AGE_SEC = 24 * 3600  # 24h
REGIME_MAX_AGE_SEC = 12 * 3600     # 12h

STRICT_MODE = os.getenv("BRAKE_HC_STRICT", "0") == "1"

# ANSI Colors
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_RESET = "\033[0m"


def pick_existing_path(candidates):
    for c in candidates:
        if Path(c).exists():
            return c
    # Fallback to the first candidate for deterministic messaging.
    return candidates[0]

def get_latest_run_dir():
    try:
        # Try helper script first
        res = subprocess.run(["bash", "scripts/get_latest_completed_dir.sh"], 
                             capture_output=True, text=True, check=True)
        return Path(res.stdout.strip())
    except:
        # Fallback manual scan
        root = Path("data/backtests")
        if not root.exists():
            return None
        summaries = sorted(root.glob("*/*/summary.json"), key=os.path.getmtime, reverse=True)
        if summaries:
            return summaries[0].parent
        return None

def check_file(path, max_age_sec=None):
    p = Path(path)
    if not p.exists():
        return "FAIL", "MISSING", None
    
    mtime = p.stat().st_mtime
    age_sec = time.time() - mtime
    age_str = f"{age_sec/3600:.1f}h ago"
    
    if max_age_sec and age_sec > max_age_sec:
        return "WARN", f"STALE ({age_str})", mtime
    
    # Try parse JSON
    try:
        with open(p, "r") as f:
            json.load(f)
    except Exception as e:
        return "FAIL", f"CORRUPT ({str(e)[:20]})", mtime
        
    return "OK", age_str, mtime

def main():
    results = []
    any_fail = False

    # 1. Freshness Table
    status, note, mtime = check_file(FRESHNESS_PATH, FRESHNESS_MAX_AGE_SEC)
    results.append({"item": "Freshness Table", "status": status, "note": note, "path": FRESHNESS_PATH})
    if status == "FAIL": any_fail = True

    # 2. Regime Monitor
    regime_path = pick_existing_path(REGIME_PATH_CANDIDATES)
    status, note, mtime = check_file(regime_path, REGIME_MAX_AGE_SEC)
    results.append({"item": "Regime Monitor", "status": status, "note": note, "path": regime_path})
    if status == "FAIL": any_fail = True

    # 3. Latest Backtest Artifacts
    run_dir = get_latest_run_dir()
    if not run_dir:
        results.append({"item": "Latest Backtest", "status": "FAIL", "note": "NO_RUNS_FOUND", "path": "data/backtests/"})
        any_fail = True
    else:
        for art in ["summary.json", "selection.json", "gate.json"]:
            path = run_dir / art
            status, note, mtime = check_file(path)
            results.append({"item": f"Backtest {art}", "status": status, "note": note, "path": str(path)})
            if status == "FAIL": any_fail = True

    # Print Table
    print("\n=== HONGSTR Brake Healthcheck ===")
    print(f"{'Item':<25} | {'Status':<6} | {'Note':<20} | {'Path'}")
    print("-" * 80)
    for r in results:
        color = C_RESET
        if r["status"] == "OK": color = C_GREEN
        elif r["status"] == "WARN": color = C_YELLOW
        elif r["status"] == "FAIL": color = C_RED
        
        print(f"{r['item']:<25} | {color}{r['status']:<6}{C_RESET} | {r['note']:<20} | {r['path']}")

    # Write JSON
    summary = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "overall_fail": any_fail,
        "results": results,
        "strict_mode": STRICT_MODE
    }
    
    try:
        os.makedirs(os.path.dirname(HEALTH_JSON_PATH), exist_ok=True)
        with open(HEALTH_JSON_PATH, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"\nSummary written to: {HEALTH_JSON_PATH}")
    except Exception as e:
        print(f"\nFailed to write JSON summary: {e}")

    # Exit Logic
    if any_fail and STRICT_MODE:
        print(f"\n{C_RED}STRICT MODE FAIL: System health degraded.{C_RESET}")
        exit(1)
    
    print(f"\n{C_GREEN}Healthcheck complete.{C_RESET}")

if __name__ == "__main__":
    main()
