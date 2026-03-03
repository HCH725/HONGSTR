#!/usr/bin/env python3
"""
scripts/coverage_update.py
Extracts stats from the latest backtest report and updates atomic coverage table.
Strictly Read-Only on core. Stability-first (exit 0).
"""
import os
import glob
import json
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ATOMIC_COVERAGE_FILE = Path("reports/state_atomic/coverage_table.jsonl")

def get_latest_backtest_summary() -> str | None:
    summaries = glob.glob("data/backtests/*/*/summary.json")
    if not summaries:
        return None
    latest = max(summaries, key=os.path.getmtime)
    return latest

def main():
    latest_summary = get_latest_backtest_summary()
    ATOMIC_COVERAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    if not latest_summary:
        logging.warning("No backtest summaries found. State unchanged.")
        return

    try:
        with open(latest_summary, "r") as f:
            summary = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read summary: {e}")
        return

    conf = summary.get("config", {})
    results = summary.get("results", {}).get("overall", {})

    # Build coverage key (best effort from summary)
    symbols = conf.get("symbols", ["UNKNOWN"])[0] 
    tfs = conf.get("timeframes", ["UNKNOWN"])[0]
    
    # Try fetching semantic versions from config, fallback to default
    sem_version = "sem_v1"
    try:
        with open("configs/semantics_version.json", "r") as f:
            sem_version = json.load(f).get("version", "sem_v1")
    except:
        pass

    cov_key = {
        "template_id": conf.get("strategy_id", "trend_mvp_v1"),
        "symbol": symbols,
        "timeframe": tfs,
        "regime": "ALL",
        "data_version": "v1",
        "semantics_version": sem_version,
        "param_space_version": "v1"
    }

    now_str = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    run_id = os.path.basename(os.path.dirname(latest_summary))

    new_record = {
        "coverage_key": cov_key,
        "status": "DONE",
        "created_utc": now_str,
        "updated_utc": now_str,
        "last_run_id": run_id,
        "notes": f"Sharpe: {results.get('sharpe_ratio', 0):.2f}, Return: {results.get('total_return', 0):.2f}"
    }

    # Load existing table to update or append
    table = []
    if ATOMIC_COVERAGE_FILE.exists():
        with open(ATOMIC_COVERAGE_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        table.append(json.loads(line))
                    except:
                        pass
    
    # Update logic (match key)
    updated = False
    for i, row in enumerate(table):
        if row.get("coverage_key") == cov_key:
            # Preserve creation time
            new_record["created_utc"] = row.get("created_utc", now_str)
            table[i] = new_record
            updated = True
            break
            
    if not updated:
        table.append(new_record)

    # Write back 
    with open(ATOMIC_COVERAGE_FILE, "w") as f:
        for row in table:
            f.write(json.dumps(row) + "\n")
            
    logging.info(f"Updated coverage table successfully for key: {cov_key}")

if __name__ == "__main__":
    main()
    exit(0)
