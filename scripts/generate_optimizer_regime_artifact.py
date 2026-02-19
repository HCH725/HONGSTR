import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


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


def generate_optimizer_regime(run_dir: Path, regime_tf: str = "4h", top_k_val: int = 5):
    summary_path = run_dir / "summary.json"
    regime_path = run_dir / "regime_report.json"
    optimizer_path = run_dir / "optimizer.json"

    summary = load_json(summary_path)
    regime_report = load_json(regime_path)
    optimizer = load_json(optimizer_path)

    if not summary or not regime_report:
        print(
            f"Error: summary.json or regime_report.json missing in {run_dir}",
            file=sys.stderr,
        )
        return

    buckets_data = regime_report.get("buckets", {})

    # We want to map the 'best' params from optimizer.json (or defaults) to these buckets  # noqa: E501
    best_params = {}
    if optimizer and "best" in optimizer:
        best_params = optimizer["best"].get("params", {})
    else:
        # Fallback to defaults or from summary/config if available
        # In this repo, vwap_supertrend is common
        best_params = {"strategy": "vwap_supertrend", "atr_period": 10, "atr_mult": 3.0}

    # Construct optimizer_regime.json
    result_buckets = {}
    for regime in ["BULL", "BEAR", "NEUTRAL"]:
        reg_metrics = buckets_data.get(regime, {})

        # Candidate construction
        # Since we currently only have one run's detailed regime slicing,
        # we treat it as the top-1 candidate for all regimes it has data for.

        candidates = []
        warnings = []

        trades_count = reg_metrics.get("trades_count", 0)
        if trades_count > 0:
            candidates.append(
                {
                    "params": best_params,
                    "score": {
                        "sharpe": reg_metrics.get("sharpe", 0.0),
                        "total_return": reg_metrics.get("total_return", 0.0),
                        "max_drawdown": reg_metrics.get("max_drawdown", 0.0),
                    },
                    "metrics": reg_metrics,
                }
            )

            if trades_count < 30:
                warnings.append(f"Insufficient samples: trades {trades_count} < 30")
        else:
            warnings.append("No trades recorded in this regime.")

        result_buckets[regime] = {
            "sample_bars": reg_metrics.get("count_periods", 0),
            "metrics": reg_metrics,
            "topk": candidates[:top_k_val],
            "warnings": warnings,
        }

    output = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_dir": str(run_dir.absolute()),
        "regime_tf": regime_tf,
        "topk": top_k_val,
        "buckets": result_buckets,
    }

    out_path = run_dir / "optimizer_regime.json"
    save_json_atomic(out_path, output)
    print(f"Generated {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate Regime-Aware Optimization Artifact"
    )
    parser.add_argument("--run_dir", required=True, help="Backtest run directory")
    parser.add_argument("--regime_tf", default="4h", help="Regime timeframe")
    parser.add_argument("--topk", type=int, default=5, help="Top K results to keep")

    args = parser.parse_args()
    generate_optimizer_regime(Path(args.run_dir), args.regime_tf, args.topk)
