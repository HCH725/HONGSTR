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

def generate_selection(run_dir: Path, regime_tf: str = "4h", top_k_val: int = 5, respect_gate: bool = True):
    regime_report_path = run_dir / "regime_report.json"
    gate_path = run_dir / "gate.json"
    optimizer_regime_path = run_dir / "optimizer_regime.json"

    # Load Inputs
    regime_report = load_json(regime_report_path)
    gate = load_json(gate_path)
    optimizer_regime = load_json(optimizer_regime_path)

    # Defaults and Warnings
    warnings = []

    # 1. Determine Regime
    current_regime = "NEUTRAL"
    if regime_report:
        current_regime = regime_report.get("latest_regime", "NEUTRAL")
    else:
        warnings.append("regime_report.json missing, defaulting to NEUTRAL")

    # 2. Determine Gate Status
    gate_overall = "UNKNOWN"
    gate_reasons = []
    if gate:
        # Gate structure: {"results": {"overall": {"pass": bool, "reasons": []}}}
        # Or flat? Checking generate_gate_artifact.py...
        # Structure is: {"generated_at":..., "results": {"overall": {"pass":..., "reasons":...}, ...}}
        res = gate.get("results", {}).get("overall", {})
        gate_pass = res.get("pass", False)
        gate_overall = "PASS" if gate_pass else "FAIL"
        gate_reasons = res.get("reasons", [])
    else:
        warnings.append("gate.json missing, gate status UNKNOWN")

    # 3. Determine Candidates from Optimizer
    candidates = []
    if optimizer_regime:
        buckets = optimizer_regime.get("buckets", {})
        reg_bucket = buckets.get(current_regime, {})
        # Copy checks to avoid mutation issues if any
        raw_candidates = reg_bucket.get("topk", [])
        # Normalizing candidate structure for selection.json if needed
        # optimizer_regime candidate: {params, score, metrics}
        # selection candidate: {rank, symbol, params, score}
        # Note: optimizer_regime currently stores params but not explicit symbol if it was portfolio optimization
        # However, for single-symbol or portfolio, params are what matters.
        # The user requested 'selected.symbol'.
        # In this context (portfolio strat), the strategy runs on all symbols config'd.
        # "symbol" in selection might mean "Primary Symbol" or "Benchmark Symbol" (BTC) or list.
        # Let's map it to the "primary" symbol usually BTCUSDT or "PORTFOLIO".
        # For now, we will use "BTCUSDT" as representative if not explicit, or list all.
        # Requirement says: "symbol": "BTCUSDT|ETHUSDT|BNBUSDT"

        for idx, c in enumerate(raw_candidates):
            cand = {
                "rank": idx + 1,
                "params": c.get("params"),
                "score": c.get("score"),
                "metrics": c.get("metrics")
            }
            candidates.append(cand)
    else:
        warnings.append("optimizer_regime.json missing")

    # 4. Make Decision
    decision = "HOLD"
    selected = None

    # Logic:
    # IF gate PASS (or !respect_gate) AND has candidates => TRADE
    # ELSE => HOLD

    can_trade = True
    if respect_gate and gate_overall != "PASS":
        can_trade = False
        warnings.append(f"Gate {gate_overall}: Trading halted.")

    if not candidates:
        can_trade = False
        warnings.append("No candidates available for this regime.")

    if can_trade:
        decision = "TRADE"
        # Select Rank 1
        best = candidates[0]
        selected = {
            "symbol": "BTCUSDT", # Default primary for now, or derive from config if available (TODO)
            "params": best["params"],
            "rank": 1,
            "score": best["score"]
        }
    else:
        # Even if HOLD, we might want to show what *would* have been selected (optional, per user req? "selected(可為null)")
        # User said "selected(可為null)"
        pass

    # Construct Output
    output = {
        "schema_version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_dir": str(run_dir.absolute()),
        "regime_tf": regime_tf,
        "regime": current_regime,
        "gate": {
            "overall": gate_overall,
            "reasons": gate_reasons
        },
        "decision": decision,
        "selected": selected,
        "candidates": candidates, # Summary of top K
        "reasons": warnings, # Mapping 'warnings' to 'reasons' field for UI
        "inputs": {
            "regime_report_path": str(regime_report_path),
            "gate_path": str(gate_path),
            "optimizer_regime_path": str(optimizer_regime_path)
        }
    }

    out_path = run_dir / "selection.json"
    save_json_atomic(out_path, output)
    print(f"Generated selection.json in {run_dir} (Decision: {decision})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Regime-Driven Selection Artifact")
    parser.add_argument("--run_dir", required=True, help="Backtest run directory")
    parser.add_argument("--regime_tf", default="4h", help="Regime timeframe")
    parser.add_argument("--topk", type=int, default=5, help="Top K results to keep")
    parser.add_argument("--respect_gate", type=str, default="true", help="Respect gate status (true/false)")

    args = parser.parse_args()
    respect = args.respect_gate.lower() == "true"

    generate_selection(Path(args.run_dir), args.regime_tf, args.topk, respect)
