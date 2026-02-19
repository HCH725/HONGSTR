import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        return None


def calibrate():
    report_path = Path("reports/walkforward_latest.json")
    if not report_path.exists():
        print(f"Error: {report_path} not found. Run walkforward suite first.")
        sys.exit(1)

    report = load_json(report_path)
    windows = report.get("windows", [])

    data_points = []
    per_symbol_counts = []

    print(f"Analyzing {len(windows)} windows...")

    for w in windows:
        if w.get("status") != "COMPLETED":
            continue

        run_dir = Path(w["run_dir"])
        summary_path = run_dir / "summary.json"
        summary = load_json(summary_path)

        if not summary:
            print(f"  Warning: No summary for {w['name']}")
            continue

        # Window Duration (Inclusive)
        start = pd.Timestamp(w["start"])
        end = pd.Timestamp(w["end"])
        window_days = (end - start).days + 1

        # Metrics
        trades = summary.get("trades_count", 0)
        exposure = summary.get("exposure_time", 0.0)

        trades_per_day = trades / window_days if window_days > 0 else 0

        # Per Symbol
        per_sym = summary.get("per_symbol", {})
        for k, v in per_sym.items():
            sym_trades = v.get("trades_count", 0)
            per_symbol_counts.append(sym_trades)
            # Check exposure per symbol/tf if needed

        data_points.append(
            {
                "window": w["name"],
                "days": window_days,
                "trades": trades,
                "trades_per_day": trades_per_day,
                "exposure": exposure,
            }
        )

        print(
            f"  {w['name']}: {window_days} days, {trades} trades ({trades_per_day:.2f}/day), Exp={exposure:.2f}"
        )

    if not data_points:
        print("No completed windows found.")
        sys.exit(0)

    # Calibration Logic
    # Target: 20th percentile for min_trades to allow 80% pass on historical data (rough heuristic)
    # or strict if recent performance is bad.
    # User requested: "PASSRATE simulation... Pick value achieving target PASSRATE in [0.6, 0.8]"

    trades_per_day_vals = [d["trades_per_day"] for d in data_points]

    # Grid Search for optimal min_trades_per_day
    candidates = np.linspace(min(trades_per_day_vals), max(trades_per_day_vals), 20)
    best_tpd = candidates[0]
    best_pass_rate = 0.0

    print("\n--- PASSRATE Simulation (Metric: Trades Per Day) ---")
    for tpd in candidates:
        # Simulate Pass Rate
        passes = sum(1 for d in data_points if d["trades_per_day"] >= tpd)
        rate = passes / len(data_points)
        print(f"  TPD >= {tpd:.4f}: Pass {passes}/{len(data_points)} ({rate:.0%})")

        # We want strictness but reasonable pass rate [0.6, 0.8]
        # Prefer higher TPD that still gives >= 60%
        if 0.6 <= rate <= 0.8:
            if tpd > best_tpd:
                best_tpd = tpd
                best_pass_rate = rate
        elif rate > 0.8 and best_pass_rate < 0.6:
            # Fallback: if we can't get into 0.6-0.8 band, take best > 0.8
            best_tpd = tpd
            best_pass_rate = rate

    # If no candidate fell in 0.6-0.8, pick the one closest to 0.7 or just 20th percentile
    if best_pass_rate < 0.1:
        p20 = np.percentile(trades_per_day_vals, 20)
        best_tpd = p20
        print(f"  Fallback to 20th percentile: {best_tpd:.4f}")

    # Portfolio Min
    # 10th percentile of absolute trades
    trades_vals = [d["trades"] for d in data_points]
    suggested_portfolio_min = max(10, int(np.percentile(trades_vals, 10)))

    # Per Symbol Min
    suggested_symbol_min = (
        max(1, int(np.percentile(per_symbol_counts, 10))) if per_symbol_counts else 5
    )

    # Exposure
    # Max observed? or 95th percentile?
    exposures = [d["exposure"] for d in data_points]
    max_exp_obs = max(exposures) if exposures else 1.0
    suggested_exposure = min(1.0, max_exp_obs * 1.05)  # Buffer
    if suggested_exposure < 0.1:
        suggested_exposure = 1.0  # Default if low usage

    print("\n--- Calibration Results ---")
    print(f"Suggested Min Trades/Day: {best_tpd:.4f}")
    print(f"Suggested Portfolio Min: {suggested_portfolio_min}")
    print(f"Suggested per-Symbol Min: {suggested_symbol_min}")
    print(f"Suggested Max Exposure: {suggested_exposure:.2f}")

    # Output Artifacts
    config = {
        "min_trades_per_day": round(best_tpd, 4),
        "min_trades_portfolio_min": suggested_portfolio_min,
        "min_trades_per_symbol_min": suggested_symbol_min,
        "per_symbol_trade_check": "WARN",
        "exposure_check": "WARN",  # Default to warn based on variance
        "max_exposure": round(suggested_exposure, 2),
        "thresholds": {
            "FULL": {
                "BULL": {"min_sharpe": 0.3, "max_mdd": -0.25},
                "BEAR": {"min_sharpe": 0.1, "max_mdd": -0.30},
                "NEUTRAL": {"min_sharpe": 0.2, "max_mdd": -0.25},
            },
            "SHORT": {"ANY": {"min_sharpe": 0.0, "max_mdd": -0.15}},
        },
    }

    out_json = Path("configs/gate_thresholds_suggested.json")
    with open(out_json, "w") as f:
        json.dump(config, f, indent=2)
    print(f"\nSaved suggested config to {out_json}")

    # MD Report
    md_content = f"""# Gate Calibration Report
**Generated At**: {datetime.utcnow().isoformat()}Z

## Window Analysis
| Window | Days | Trades | T/Day | Exposure |
|---|---|---|---|---|
"""
    for d in data_points:
        md_content += f"| {d['window']} | {d['days']} | {d['trades']} | {d['trades_per_day']:.3f} | {d['exposure']:.2f} |\n"

    md_content += f"""
## Suggestions
- **Min Trades Per Day**: {best_tpd:.4f} (Targeting ~{best_pass_rate:.0%} pass rate)
- **Portfolio Min Trades**: {suggested_portfolio_min}
- **Per-Symbol Min Trades**: {suggested_symbol_min}
- **Max Exposure**: {suggested_exposure:.2f}

## Action
Copy `configs/gate_thresholds_suggested.json` to `configs/gate_thresholds.json` to apply.
"""
    with open("reports/gate_calibration_latest.md", "w") as f:
        f.write(md_content)
    print("Saved report to reports/gate_calibration_latest.md")


if __name__ == "__main__":
    calibrate()
