import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate optimizer.json stub for a backtest run")
    parser.add_argument("--dir", type=str, required=True, help="Backtest run directory")
    args = parser.parse_args()

    run_dir = Path(args.dir)
    if not run_dir.exists():
        print(f"Error: Directory {run_dir} not found", file=sys.stderr)
        sys.exit(1)

    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        print(f"Error: summary.json not found in {run_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(summary_path, 'r') as f:
            summary = json.load(f)
    except Exception as e:
        print(f"Error reading summary.json: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract info for stub
    run_id = summary.get("run_id", "unknown")
    timestamp = summary.get("timestamp", datetime.utcnow().isoformat())
    config = summary.get("config", {})

    # Construct Optimizer Stub
    # Schema: schema_version, run_id, timestamp, data_scope, objective, search, best, top_k

    optimizer_data = {
        "schema_version": "1.0",
        "run_id": run_id,
        "timestamp": timestamp,
        "data_scope": {
            "symbols": config.get("symbols", []),
            "timeframes": config.get("timeframes", []),
            "start": "N/A", # Not in summary config usually, but could be inferred or skipped
            "end": "N/A"
        },
        "objective": {
            "metric": "sharpe", # Default assumption
            "direction": "maximize"
        },
        "search": {
            "method": "grid",
            "budget": 1 # Single run
        },
        "best": {
            "params": {
                # Extract strategy params if possible, or just dump config
                "strategy": "vwap_supertrend", # Hardcoded for now based on context
                "atr_period": 10, # Defaults from run_backtest.py if not in config
                "atr_mult": 3.0   # Defaults
            },
            "metrics_portfolio": {
                "total_return": summary.get("total_return"),
                "sharpe": summary.get("sharpe"),
                "max_drawdown": summary.get("max_drawdown")
            },
            "metrics_per_symbol": summary.get("per_symbol", {})
        },
        "top_k": [] # Empty for single run
    }

    # Write atomic
    out_path = run_dir / "optimizer.json"
    tmp_path = run_dir / "optimizer.json.tmp"

    with open(tmp_path, 'w') as f:
        json.dump(optimizer_data, f, indent=2)

    os.rename(tmp_path, out_path)
    print(f"Generated optimizer.json in {run_dir}")

if __name__ == "__main__":
    main()
