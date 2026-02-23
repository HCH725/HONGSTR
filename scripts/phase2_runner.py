#!/usr/bin/env python3
"""
scripts/phase2_runner.py
Phase 2 Strategy Analysis - Param Sweep Expansion Runner.
Enforces read-only and parallel IS/OOS backtesting.
"""
import argparse
import json
import logging
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from itertools import product
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def run_backtest(strategy, symbols, tfs, start, end, run_id, params):
    cmd = [
        ".venv/bin/python", "scripts/run_backtest.py",
        "--strategy", strategy,
        "--symbols", symbols,
        "--timeframes", tfs,
        "--start", start,
        "--end", end,
        "--run_id", run_id,
        "--params-json", json.dumps(params)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        # Verify success by checking summary.json existence
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        expected_dir = Path("data/backtests") / today_str / run_id
        if expected_dir.exists() and (expected_dir / "summary.json").exists():
            return True, expected_dir, run_id
        else:
            logging.error(f"Run {run_id} failed. Stdout: {res.stdout[-200:]} Stderr: {res.stderr[-200:]}")
            return False, "", run_id
    except Exception as e:
        logging.error(f"Exception for {run_id}: {e}")
        return False, "", run_id

def main():
    parser = argparse.ArgumentParser(description="Phase 2 Param Sweep Runner")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframes", required=True)
    parser.add_argument("--is-start", required=True)
    parser.add_argument("--is-end", required=True)
    parser.add_argument("--oos-start", required=True)
    parser.add_argument("--oos-end", required=True)
    parser.add_argument("--param-space", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index_file = out_dir / "run_index.tsv"

    # Load Param Space
    with open(args.param_space, "r") as f:
        space = json.load(f)
    
    grid = space.get("grid", {})
    keys = list(grid.keys())
    values = [grid[k] for k in keys]
    combinations = [dict(zip(keys, v)) for v in product(*values)]
    
    candidates = []
    for i, params in enumerate(combinations):
        candidates.append((f"P2C{i+1:02d}", params))
    
    logging.info(f"Starting Phase 2 with {len(candidates)} candidates.")

    def worker(c_id, params):
        results = []
        # Run IS
        rid_is = f"p2_{c_id}_is"
        ok_is, dir_is, _ = run_backtest(args.strategy, args.symbols, args.timeframes, args.is_start, args.is_end, rid_is, params)
        if ok_is:
            results.append(f"{c_id}\t{rid_is}\tIS\t{json.dumps(params)}\t{dir_is}\n")
        
        # Run OOS
        rid_oos = f"p2_{c_id}_oos"
        ok_oos, dir_oos, _ = run_backtest(args.strategy, args.symbols, args.timeframes, args.oos_start, args.oos_end, rid_oos, params)
        if ok_oos:
            results.append(f"{c_id}\t{rid_oos}\tOOS\t{json.dumps(params)}\t{dir_oos}\n")
        return results

    # Run in parallel
    with open(index_file, "w") as f:
        # f.write("candidate_id\trun_id\tmode\tparams\tout_dir\n") # No header as per Phase 1 pattern
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, cid, p) for cid, p in candidates]
            for future in as_completed(futures):
                try:
                    lines = future.result()
                    for line in lines:
                        f.write(line)
                    f.flush()
                except Exception as e:
                    logging.error(f"Worker iteration failed: {e}")

    logging.info(f"Phase 2 runner finished. Index updated at {index_file}")

if __name__ == "__main__":
    main()
