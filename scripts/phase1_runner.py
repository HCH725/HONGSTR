#!/usr/bin/env python3
"""
scripts/phase1_runner.py
Phase 1 Strategy Analysis - Candidate Grid Runner.
Runs hardcoded IS/OOS splits for candidates.
Read-Only constraints strictly enforced. exits 0.
"""
import json
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STRATEGY = "vwap_supertrend"
SYMBOLS = "BTCUSDT,ETHUSDT,BNBUSDT"
TIMEFRAMES = "1h,4h"

IS_START = "2020-01-01"
IS_END = "2024-12-31"

OOS_START = "2025-01-01"
OOS_END = "now"

OUT_DIR = Path("reports/strategy_research/phase1")
INDEX_FILE = OUT_DIR / "run_index.tsv"

def check_coverage_gate():
    logging.info("Checking data coverage gate...")
    try:
        res = subprocess.run(["bash", "scripts/check_data_coverage.sh"], capture_output=True, text=True)
        if "OVERALL_STATUS=PASS" not in res.stdout:
            logging.error("COVERAGE GATE FAILED. OVERALL_STATUS is not PASS.")
            logging.error(f"Tail of output: {res.stdout[-500:]}")
            return False
        return True
    except Exception as e:
        logging.error(f"Failed to run coverage check: {e}")
        return False

def run_backtest(params, is_oos=False, c_id=""):
    start = OOS_START if is_oos else IS_START
    end = OOS_END if is_oos else IS_END
    mode = "OOS" if is_oos else "IS"
    
    run_id = f"p1_{c_id}_{mode}"
    cmd = [
        ".venv/bin/python", "scripts/run_backtest.py",
        "--strategy", STRATEGY,
        "--symbols", SYMBOLS,
        "--timeframes", TIMEFRAMES,
        "--start", start,
        "--end", end,
        "--run_id", run_id,
        "--params-json", json.dumps(params)
    ]
    
    logging.info(f"Running {mode} for Candidate {c_id}...")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Check standard dir
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        expected_dir = Path("data/backtests") / today_str / run_id
        if expected_dir.exists() and (expected_dir / "summary.json").exists():
            return True, expected_dir, run_id
        else:
            logging.error(f"{mode} Run failed. Output:\n{res.stderr}")
            return False, "", run_id
    except Exception as e:
        logging.error(f"Exception during run: {e}")
        return False, "", run_id

def main():
    if not check_coverage_gate():
        logging.error("ABORTING Phase 1 due to coverage failure.")
        exit(0)
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate Grid
    candidates = []
    c_idx = 1
    # Minimum required: 10, 14 for period | 2.5, 3.0 for mult (plus 1 expansion)
    for atr_period in [10, 14, 20]:
        for atr_mult in [2.5, 3.0]:
            p = {"atr_period": atr_period, "atr_mult": atr_mult}
            candidates.append((f"C{c_idx}", p))
            c_idx += 1
                
    logging.info(f"Generated {len(candidates)} candidates.")
    
    # Worker definition
    def run_candidate(c_id, params):
        results = []
        # IS
        ok_is, dir_is, rid_is = run_backtest(params, is_oos=False, c_id=c_id)
        if ok_is:
            results.append(f"{c_id}\t{rid_is}\tIS\t{json.dumps(params)}\t{dir_is}\n")
        # OOS
        ok_oos, dir_oos, rid_oos = run_backtest(params, is_oos=True, c_id=c_id)
        if ok_oos:
            results.append(f"{c_id}\t{rid_oos}\tOOS\t{json.dumps(params)}\t{dir_oos}\n")
        return results

    # Execute in Parallel
    with open(INDEX_FILE, "a") as f:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(run_candidate, c_id, params) for c_id, params in candidates]
            for future in as_completed(futures):
                try:
                    res_lines = future.result()
                    for line in res_lines:
                        f.write(line)
                    f.flush()
                except Exception as e:
                    logging.error(f"Candidate batch failed: {e}")
                    
    logging.info("Phase 1 candidate execution completed.")

if __name__ == "__main__":
    main()
    exit(0)
