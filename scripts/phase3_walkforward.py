#!/usr/bin/env python3
"""
scripts/phase3_walkforward.py
Phase 3 Walkforward Validation Runner.
- Loads Top-10 candidates from Phase 2.
- Iterates through 6-month sliding windows.
- Calibrates (selects best) on IS, then validates on OOS.
"""
import argparse
import json
import logging
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
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
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        expected_dir = Path("data/backtests") / today_str / run_id
        if expected_dir.exists() and (expected_dir / "summary.json").exists():
            return True, expected_dir
        else:
            logging.error(f"Backtest {run_id} failed. Stdout: {res.stdout[-100:]}")
            return False, None
    except Exception as e:
        logging.error(f"Exception for {run_id}: {e}")
        return False, None

def evaluate_run(summary_path, gates):
    if not summary_path or not summary_path.exists():
        return -999.0
    try:
        with open(summary_path, "r") as f:
            data = json.load(f)
        
        sharpe = data.get("sharpe", 0.0)
        mdd = data.get("max_drawdown", 0.0)
        trades = data.get("trades_count", 0)

        score = sharpe
        # Penalties based on phase1_gates (standardized)
        if mdd < gates.get("max_mdd_is", -0.35): score -= 1.0
        if trades < gates.get("min_trades_is", 300): score -= 0.5
        if sharpe < gates.get("min_sharpe_is", 0.5): score -= 0.5
        
        return score
    except Exception as e:
        logging.error(f"Eval error for {summary_path}: {e}")
        return -999.0

def main():
    parser = argparse.ArgumentParser(description="Phase 3 Walkforward Runner")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, "r") as f:
        conf = json.load(f)
    
    # 1. Load Candidates (Top 10 from Phase 2)
    cand_source = Path(conf["candidate_source"])
    if not cand_source.exists():
        logging.error(f"Candidate source {cand_source} not found.")
        return
    with open(cand_source, "r") as f:
        p2_data = json.load(f)
    
    top_10_params = [c["params"] for c in p2_data.get("candidates", [])[:10]]
    logging.info(f"Loaded {len(top_10_params)} candidates from Phase 2.")

    # 2. Load Gates
    gates_path = Path(conf["gates_config"])
    with open(gates_path, "r") as f:
        gates = json.load(f)

    out_dir = Path("reports/strategy_research/phase3")
    out_dir.mkdir(parents=True, exist_ok=True)
    index_file = out_dir / "run_index.tsv"

    with open(index_file, "w") as idx_f:
        for win in conf["windows"]:
            w_name = win["name"]
            logging.info(f"--- Processing {w_name} ---")

            # A. Phase: IS Selection
            is_results = []
            def is_worker(idx, p):
                rid = f"p3_{w_name}_is_{idx}"
                ok, pdir = run_backtest(conf["strategy"], conf["symbols"], conf["timeframes"], win["is_start"], win["is_end"], rid, p)
                if ok:
                    score = evaluate_run(pdir / "summary.json", gates)
                    return {"params": p, "score": score, "dir": str(pdir)}
                return None

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(is_worker, i, p) for i, p in enumerate(top_10_params)]
                for fut in as_completed(futures):
                    res = fut.result()
                    if res: is_results.append(res)
            
            if not is_results:
                logging.error(f"No valid IS results for {w_name}. Skipping window.")
                continue
            
            # Select Best (highest score)
            best_is = max(is_results, key=lambda x: x["score"])
            best_params = best_is["params"]
            logging.info(f"Window {w_name}: Selected best params {best_params} with IS Score {best_is['score']:.2f}")

            # B. Phase: OOS Validation
            rid_oos = f"p3_{w_name}_oos"
            ok_oos, pdir_oos = run_backtest(conf["strategy"], conf["symbols"], conf["timeframes"], win["oos_start"], win["oos_end"], rid_oos, best_params)
            
            if ok_oos:
                # Log entry: window_name | run_id | mode | params | dir
                line = f"{w_name}\t{rid_oos}\tOOS\t{json.dumps(best_params)}\t{pdir_oos}\n"
                idx_f.write(line)
                idx_f.flush()
                logging.info(f"Window {w_name} OOS complete.")

    logging.info("Phase 3 Walkforward Runner Finished.")

if __name__ == "__main__":
    main()
