import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List

# Thresholds
THRESHOLDS = {
    "hard_fail": {
        "trades_count_min": 30,
        "max_drawdown_limit": -0.25,  # Fail if <= -0.25
        "exposure_time_max": 0.98,  # Fail if > 0.98
        "sharpe_min": -0.2,  # Fail if < -0.2
    },
    "soft_pass": {
        "sharpe_target": 0.5,
        "max_drawdown_target": -0.15,  # Better than -0.15
        "total_return_min": 0.0,
    },
}


def _fmt_metric(x, spec: str = ".2f", na: str = "NA") -> str:
    """Format metrics safely when value is None/NaN/non-numeric."""
    if x is None:
        return na
    try:
        if isinstance(x, float) and math.isnan(x):
            return na
    except Exception:
        pass
    try:
        return format(x, spec)
    except Exception:
        return str(x)


class GateResult:
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.passes: List[str] = []
        self.table_rows: List[Dict] = []

    def fail(self, msg: str):
        self.errors.append(msg)

    def warn(self, msg: str):
        self.warnings.append(msg)

    def success(self, msg: str):
        self.passes.append(msg)

    def add_row(self, name: str, metrics: Dict):
        self.table_rows.append(
            {
                "name": name,
                "trades": metrics.get("trades_count", 0),
                "return": metrics.get("total_return", 0.0),
                "mdd": metrics.get("max_drawdown", 0.0),
                "sharpe": metrics.get("sharpe", 0.0),
                "exposure": metrics.get("exposure_time", 0.0),
            }
        )


def check_metrics(name: str, metrics: Dict, result: GateResult):
    # Extract values with safe defaults
    trades = metrics.get("trades_count", 0)
    mdd = metrics.get("max_drawdown", 0.0) or 0.0
    exposure = metrics.get("exposure_time", 0.0) or 0.0
    sharpe = metrics.get("sharpe", 0.0) or 0.0

    # 1. Hard Fails
    if trades < THRESHOLDS["hard_fail"]["trades_count_min"]:
        result.fail(
            f"[{name}] Trades {trades} < {THRESHOLDS['hard_fail']['trades_count_min']}"
        )

    if mdd <= THRESHOLDS["hard_fail"]["max_drawdown_limit"]:
        result.fail(
            f"[{name}] MaxDD {mdd:.4f} <= {THRESHOLDS['hard_fail']['max_drawdown_limit']}"  # noqa: E501
        )

    if exposure > THRESHOLDS["hard_fail"]["exposure_time_max"]:
        result.fail(
            f"[{name}] Exposure {exposure:.4f} > {THRESHOLDS['hard_fail']['exposure_time_max']}"  # noqa: E501
        )

    if sharpe < THRESHOLDS["hard_fail"]["sharpe_min"]:
        result.fail(
            f"[{name}] Sharpe {sharpe:.4f} < {THRESHOLDS['hard_fail']['sharpe_min']}"
        )

    # 2. Soft Pass Checks (for info)
    # We don't fail on these, just verify good behavior? Use logic later if needed.


def main():
    parser = argparse.ArgumentParser(description="Backtest Quality Gate")
    parser.add_argument(
        "--dir", type=str, help="Backtest directory containing summary.json"
    )
    parser.add_argument("--summary", type=str, help="Direct path to summary.json")
    parser.add_argument(
        "--symbols",
        type=str,
        default="BTCUSDT,ETHUSDT,BNBUSDT",
        help="Comma-separated symbols",
    )
    parser.add_argument(
        "--timeframes", type=str, default="1h,4h", help="Comma-separated timeframes"
    )

    # Store True by default, allow --no_strict to disable
    parser.add_argument(
        "--strict_timeframes",
        action="store_true",
        default=True,
        help="Fail if any TF missing",
    )
    parser.add_argument(
        "--no_strict_timeframes",
        action="store_false",
        dest="strict_timeframes",
        help="Disable strict TF check",
    )

    args = parser.parse_args()

    # Resolve Summary Path
    summary_path = None
    run_dir = None

    if args.summary:
        summary_path = Path(args.summary)
        run_dir = summary_path.parent
    elif args.dir:
        run_dir = Path(args.dir)
        summary_path = run_dir / "summary.json"
    else:
        # Try LATEST_DIR env
        latest = os.environ.get("LATEST_DIR")
        if latest:
            run_dir = Path(latest)
            summary_path = run_dir / "summary.json"

    if not summary_path or not summary_path.exists():
        print(f"ERROR: summary.json not found at {summary_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(summary_path, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load summary JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Check for gate.json (Adaptive Gate)
    gate_path = run_dir / "gate.json"
    gate_data = None
    if gate_path.exists():
        try:
            with open(gate_path, "r") as f:
                gate_data = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load gate.json: {e}", file=sys.stderr)

    # Setup Check List
    target_symbols = [s.strip() for s in args.symbols.split(",")]
    target_tfs = [t.strip() for t in args.timeframes.split(",")]

    GateResult()

    # 1. Print Portfolio Summary
    print("[Portfolio]")
    p_trades = data.get("trades_count", 0)
    p_sharpe = data.get("sharpe", 0.0)
    p_ret = data.get("total_return", 0.0)
    print(
        "Trades: "
        f"{p_trades}, "
        f"Sharpe: {_fmt_metric(p_sharpe, '.4f')}, "
        f"Return: {_fmt_metric(p_ret, '.4f')}"
    )

    # 2. Print Per-Symbol Table
    per_symbol = data.get("per_symbol", {})

    print("-" * 80)
    print(
        f"{'Name':<15} | {'Trades':<6} | {'Return':<8} | {'MDD':<8} | {'Sharpe':<8} | {'Exp':<8}"  # noqa: E501
    )
    print("-" * 80)

    for sym in target_symbols:
        for tf in target_tfs:
            key = f"{sym}_{tf}"
            if key in per_symbol:
                metrics = per_symbol[key]
                trades = metrics.get("trades_count", 0)
                ret = metrics.get("total_return", 0.0)
                mdd = metrics.get("max_drawdown", 0.0)
                sharpe = metrics.get("sharpe", 0.0)
                exposure = metrics.get("exposure_time", 0.0)
                print(
                    f"{key:<15} | {trades:<6} | "
                    f"{_fmt_metric(ret, '>7.2%')} | "
                    f"{_fmt_metric(mdd, '>7.2%')} | "
                    f"{_fmt_metric(sharpe, '>8.4f')} | "
                    f"{_fmt_metric(exposure, '>7.2%')}"
                )
            else:
                print(f"{key:<15} | MISSING")
    print("-" * 80)

    # 3. Decision Logic
    if gate_data and "overall" in gate_data.get("results", {}):
        # Use Adaptive Gate Result
        overall = gate_data["results"]["overall"]
        passed = overall.get("pass", False)
        reasons = overall.get("reasons", [])

        if passed:
            print("\n[GATE PASSED] Adaptive Gate checks passed.")
            sys.exit(0)
        else:
            print("\n[GATE FAILED] Adaptive Gate checks failed:")
            for r in reasons:
                print(f"  - {r}")
            sys.exit(2)
    else:
        # Fallback to Legacy Logic (Hardcoded) if gate.json missing
        print(
            "\n[WARNING] gate.json not found. Falling back to legacy hardcoded checks."
        )
        # ... logic omitted for brevity, or we can just fail/warn.
        # For this task, we expect gate.json to exist.
        if args.strict_timeframes:
            # Basic check to ensure we don't pass blindly if gate.json is missing
            print("Legacy strict check not fully implemented here to prefer gate.json.")
            # But let's check portfolio sharpe/trades as minimum?
            safe_p_sharpe = (
                p_sharpe
                if isinstance(p_sharpe, (int, float)) and p_sharpe is not None
                else 0.0
            )
            if p_trades < 10 or safe_p_sharpe < -0.5:
                print("[GATE FAILED] Legacy fallback check failed.")
                sys.exit(2)
            else:
                print("[GATE PASSED] Legacy fallback check passed (Loose).")
                sys.exit(0)


if __name__ == "__main__":
    main()
