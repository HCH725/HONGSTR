import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Default Config
DEFAULT_CONFIG = {
  "min_trades_per_day": 0.5,
  "min_trades_portfolio_min": 30,
  "min_trades_per_symbol_min": 5,
  "per_symbol_trade_check": "WARN",
  "exposure_check": "OFF",
  "max_exposure": 1.0,
  "thresholds": {
    "FULL": {
      "BULL": {"min_sharpe": 0.3, "max_mdd": -0.25},
      "BEAR": {"min_sharpe": 0.1, "max_mdd": -0.30},
      "NEUTRAL": {"min_sharpe": 0.2, "max_mdd": -0.25}
    },
    "SHORT": {
      "BULL": {"min_sharpe": 0.0, "max_mdd": -0.15},
      "BEAR": {"min_sharpe": 0.0, "max_mdd": -0.15},
      "NEUTRAL": {"min_sharpe": 0.0, "max_mdd": -0.15}
    }
  }
}

def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}", file=sys.stderr)
        return None

def save_json_atomic(path: Path, data: Dict):
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.rename(tmp_path, path)

def generate_gate(run_dir: Path, mode: str, symbols: List[str], timeframe: str):
    regime_path = run_dir / "regime_report.json"
    summary_path = run_dir / "summary.json"
    config_path = Path("configs/gate_thresholds.json")

    regime_data = load_json(regime_path)
    summary_data = load_json(summary_path)

    # Load Config or Default
    gate_config = load_json(config_path)
    if not gate_config:
        print(f"Warning: {config_path} not found. Using defaults.", file=sys.stderr)
        gate_config = DEFAULT_CONFIG

    if not regime_data or not summary_data:
        print(f"Error: Run artifacts missing in {run_dir} (regime or summary)", file=sys.stderr)
        sys.exit(1)

    # Calculate Window Days
    start_ts = pd.Timestamp(summary_data["start_ts"])
    end_ts = pd.Timestamp(summary_data["end_ts"])
    window_days = (end_ts - start_ts).days + 1

    # Calculate Required Trades
    min_trades_per_day = gate_config.get("min_trades_per_day", 0.5)
    portfolio_min = gate_config.get("min_trades_portfolio_min", 30)
    symbol_min = gate_config.get("min_trades_per_symbol_min", 5)

    required_trades = max(portfolio_min, int(window_days * min_trades_per_day))

    # Thresholds Lookup
    thresholds = gate_config.get("thresholds", DEFAULT_CONFIG["thresholds"])
    norm_mode = mode.upper()
    if norm_mode not in thresholds:
        effective_thresholds = thresholds.get("SHORT", DEFAULT_CONFIG["thresholds"]["SHORT"])
    else:
        effective_thresholds = thresholds[norm_mode]

    buckets = regime_data.get("buckets", {})
    results_by_regime = {}
    overall_pass = True
    overall_reasons = []

    # 1. Global Checks (Portfolio Trades)
    portfolio_trades = summary_data.get("trades_count", 0)
    if portfolio_trades < required_trades:
        overall_pass = False
        overall_reasons.append(f"Portfolio Trades {portfolio_trades} < Required {required_trades} (Window: {window_days}d)")

    # 2. Per Symbol Checks
    per_symbol_check = gate_config.get("per_symbol_trade_check", "WARN")
    if per_symbol_check != "OFF":
        per_symbol_data = summary_data.get("per_symbol", {})
        for sym in symbols:
            # Handle potential missing symbol in summary if no trades
            sym_data = per_symbol_data.get(f"{sym}_1h", {}) # Try 1h first? or iterate all keys?
            # Actually summary keys are usually SYM_TF. We should verify.
            # But let's look at regime data per symbol if available?
            # Regime report aggregates by regime. Summary aggregates by sym_tf.
            # Let's sum trades for symbol across TFs from summary per_symbol
            s_trades = 0
            found = False
            for k, v in per_symbol_data.items():
                if k.startswith(sym):
                    s_trades += v.get("trades_count", 0)
                    found = True

            if s_trades < symbol_min:
                msg = f"Symbol {sym} Trades {s_trades} < {symbol_min}"
                if per_symbol_check == "FAIL":
                    overall_pass = False
                    overall_reasons.append(msg)
                else:
                    # Append to reasons but don't fail unless it's only warning
                    # actually we should probably log it in result but not fail overall_pass
                    pass # Just logging in per-regime or separate section?
                    # Let's add loop warning to overall reasons with [WARN] prefix?
                    overall_reasons.append(f"[WARN] {msg}")

    # 3. Exposure Check
    exposure_check = gate_config.get("exposure_check", "OFF")
    if exposure_check != "OFF":
        max_exp = gate_config.get("max_exposure", 1.0)
        # Check global exposure time or max exposure?
        # User requested max_exposure semantics.
        # Summary has exposure_time. It doesn't have peak leverage.
        # Assuming we check exposure_time for now as proxy for "over-exposed"
        # OR if we had max_exposure metrics.
        # Retaining logic from previous issue: "Exposure 0.99 > 0.98".
        obs_exp = summary_data.get("exposure_time", 0.0)

        # NOTE: logic in previous fail was > 0.98.
        # If gate_config has max_exposure 1.0, and obs is 0.99, it passes.
        # If gate_config has max_exposure 0.98, and obs is 0.99, it fails.
        if obs_exp > max_exp:
             msg = f"Exposure {obs_exp:.2f} > {max_exp}"
             if exposure_check == "FAIL":
                 overall_pass = False
                 overall_reasons.append(msg)
             else:
                 overall_reasons.append(f"[WARN] {msg}")

    # 4. Per Regime Checks
    for reg in ["BULL", "BEAR", "NEUTRAL"]:
        bucket = buckets.get(reg, {})
        sharpe = float(bucket.get("sharpe", 0.0))
        mdd = float(bucket.get("max_drawdown", 0.0))
        # Total trades in this regime
        reg_trades = int(bucket.get("trades_count", 0))

        # Fallback to ANY if specific regime not defined
        thresh = effective_thresholds.get(reg, effective_thresholds.get("ANY", {}))

        if not thresh:
             # Should not happen with default config
             thresh = {"min_sharpe": 0.0, "max_mdd": -1.0}

        reg_pass = True
        reg_reasons = []

        # Check Sharpe
        if sharpe < thresh.get("min_sharpe", 0):
            reg_pass = False
            reg_reasons.append(f"sharpe {sharpe:.2f} < {thresh['min_sharpe']:.2f}")

        # Check MDD
        if mdd < thresh.get("max_mdd", -1.0):
            reg_pass = False
            reg_reasons.append(f"max_mdd {mdd:.2f} < {thresh['max_mdd']:.2f}")

        # We generally don't check trade count PER REGIME for failure here if we check global
        # But we could if config had it. Config structure in prompt doesn't strictly have per-regime min_trades.
        # It has global dynamic. So we skip per-regime trade check or keep it loose?
        # User said "Replace hard-coded trade-count gate thresholds with adaptive..."
        # So we trust global/portfolio check.

        results_by_regime[reg] = {
            "sharpe": sharpe,
            "max_mdd": mdd,
            "trades": reg_trades,
            "pass": reg_pass,
            "reasons": reg_reasons
        }

        if not reg_pass:
            overall_pass = False
            for r in reg_reasons:
                overall_reasons.append(f"{reg}: {r}")

    gate_data = {
        "schema_version": 2,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_dir": str(run_dir.absolute()),
        "inputs": {
            "timeframe_regime": timeframe,
            "symbols": symbols,
            "mode": mode,
            "window_days": window_days,
            "required_trades": required_trades
        },
        "config": gate_config,
        "results": {
            "by_regime": results_by_regime,
            "overall": {
                "pass": overall_pass,
                "reasons": overall_reasons,
                "portfolio_trades": portfolio_trades,
                "exposure": summary_data.get("exposure_time", 0.0)
            }
        }
    }

    gate_path = run_dir / "gate.json"
    save_json_atomic(gate_path, gate_data)
    print(f"Generated {gate_path} (Overall: {'PASS' if overall_pass else 'FAIL'})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Regime Quality Gate Artifact")
    parser.add_argument("--dir", required=True, help="Backtest run results directory")
    parser.add_argument("--mode", required=True, choices=["FULL", "SHORT", "custom"], help="Backtest mode")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    parser.add_argument("--timeframe", default="4h", help="Regime timeframe")

    args = parser.parse_args()

    symbols_list = [s.strip() for s in args.symbols.split(",")]
    generate_gate(Path(args.dir), args.mode, symbols_list, args.timeframe)
