#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REPO = Path(REPO_ROOT)

SCRIPTS_DIR = os.path.join(REPO_ROOT, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from _ssot_meta import add_ssot_meta
except ImportError:
    # Handle the fact that _ssot_meta was mysteriously deleted earlier
    def add_ssot_meta(payload: dict, source_paths=None, notes: str = "") -> dict:
        import hashlib
        now_utc = datetime.now(timezone.utc)
        meta = {
            "schema_version": "1.0",
            "producer_git_sha": "UNKNOWN",
            "generated_utc": now_utc.isoformat(),
            "source_inputs": [],
            "notes": notes
        }
        meta.update(payload)
        return meta

OUTPUT_SSOT = REPO / "data/state/cost_sensitivity_matrix_latest.json"
BACKTESTS_DIR = REPO / "data/backtests"

def compute_delta(baseline_val, scenario_val):
    if baseline_val is None or scenario_val is None:
        return None
    try:
        return float(baseline_val) - float(scenario_val)
    except:
        return None

def build_cost_sensitivity_matrix() -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    lookback_days = 7
    window_start = now_utc - timedelta(days=lookback_days)

    candidates = []
    
    # 1. Glob discovery strictly on data/backtests/**/summary.json
    for summary_path in BACKTESTS_DIR.rglob("summary.json"):
        if not summary_path.is_file():
            continue
            
        try:
            mtime = summary_path.stat().st_mtime
            mtime_utc = datetime.fromtimestamp(mtime, tz=timezone.utc)
        except OSError:
            continue

        if mtime_utc < window_start:
            continue

        candidates.append({
            "path": summary_path,
            "mtime": mtime,
            "mtime_utc": mtime_utc
        })

    # Sort descending by mtime
    candidates.sort(key=lambda x: x["mtime"], reverse=True)
    top_candidates = candidates[:5]

    totals = {
        "runs_seen": len(top_candidates),
        "rows": 0,
        "ok": 0,
        "warn": 0,
        "unknown": 0
    }

    rows = []
    source_inputs = []
    
    for c in top_candidates:
        summary_path = c["path"]
        
        # Determine relative paths strictly
        try:
            rel_path = summary_path.relative_to(REPO)
        except ValueError:
            rel_path = summary_path
            
        run_dir = summary_path.parent
        run_id = run_dir.name
        
        source_inputs.append(str(rel_path))

        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
        except Exception:
            rows.append({
                "run_id": run_id,
                "strategy": "UNKNOWN",
                "status": "UNKNOWN",
                "reasons": ["PARSE_ERROR"],
                "baseline": {},
                "cost_x1_2": None,
                "cost_x1_5": None,
                "deltas": {},
                "evidence": [{"label": "run_summary", "path": str(rel_path)}]
            })
            totals["rows"] += 1
            totals["unknown"] += 1
            continue

        # Check for multiple symbols/strategies in summary.json
        # HONGSTR often embeds the strategies under "per_symbol" or uses a flat structure
        per_symbol = s_data.get("per_symbol", {})
        if not per_symbol:
            # Maybe flat single strategy
            strategy = s_data.get("strategy") or "UNKNOWN_STRAT"
            strategies_to_process = [(strategy, s_data)]
        else:
            strategies_to_process = [(sym, data) for sym, data in per_symbol.items()]

        for strat_name, strat_data in strategies_to_process:
            row_status = "UNKNOWN"
            reasons = []
            
            # 1. Parse baseline metrics tolerantly
            baseline = {}
            for field, alias in [("sharpe", "sharpe"), ("max_drawdown", "mdd"), ("total_return", "ret"), ("trades_count", "trades")]:
                val = strat_data.get(field)
                if val is None:
                    # try alternative names
                    val = strat_data.get(alias)
                    
                if val is not None:
                    baseline[alias] = val
                    
            if "sharpe" not in baseline or "ret" not in baseline:
                reasons.append("MISSING_METRIC")
                row_status = "UNKNOWN"
            else:
                row_status = "OK"

            # 2. Look for explicit alternative cost metrics in artifacts
            # Currently HONGSTR doesn't generate "scenarios", so these will gracefully populate as missing
            scenarios = strat_data.get("scenarios", {})
            cost_x1_2 = scenarios.get("cost_x1_2")
            cost_x1_5 = scenarios.get("cost_x1_5")
            
            deltas = {}
            if cost_x1_2 and isinstance(cost_x1_2, dict):
                deltas["sharpe_drop_20"] = compute_delta(baseline.get("sharpe"), cost_x1_2.get("sharpe"))
                deltas["ret_drop_20"] = compute_delta(baseline.get("ret"), cost_x1_2.get("ret"))
            if cost_x1_5 and isinstance(cost_x1_5, dict):
                deltas["sharpe_drop_50"] = compute_delta(baseline.get("sharpe"), cost_x1_5.get("sharpe"))
                deltas["ret_drop_50"] = compute_delta(baseline.get("ret"), cost_x1_5.get("ret"))

            if not cost_x1_2 and not cost_x1_5 and "MISSING_METRIC" not in reasons:
                reasons.append("ONLY_BASELINE_AVAILABLE")

            # Final status logic
            if "MISSING_METRIC" in reasons:
                row_status = "UNKNOWN"
            elif "ONLY_BASELINE_AVAILABLE" in reasons:
                # Still technically "OK" because we simply lack the alt scenarios right now. 
                row_status = "OK" 

            totals["rows"] += 1
            if row_status == "OK":
                totals["ok"] += 1
            elif row_status == "WARN":
                totals["warn"] += 1
            else:
                totals["unknown"] += 1

            rows.append({
                "run_id": run_id,
                "strategy": strat_name,
                "status": row_status,
                "reasons": reasons,
                "baseline": baseline,
                "cost_x1_2": cost_x1_2,
                "cost_x1_5": cost_x1_5,
                "deltas": deltas,
                "evidence": [
                    {"label": "run_summary", "path": str(rel_path)}
                ]
            })

    # The overall status defines ONLY the producer's pipeline generator health.
    overall = "OK"
    refresh_hint = ""
    if totals["runs_seen"] == 0:
        overall = "WARN"
        refresh_hint = "No backtest summaries found in last 7 days."
    elif totals["unknown"] > 0 and totals["ok"] == 0:
        overall = "WARN"
        refresh_hint = "All parsed runs generated UNKNOWN rows due to missing baseline metrics."

    payload = {
        "overall": overall,
        "scenarios": [
            {"id": "baseline", "label": "baseline"},
            {"id": "cost_x1_2", "label": "cost +20%"},
            {"id": "cost_x1_5", "label": "cost +50%"}
        ],
        "window": {
            "lookback_days": lookback_days,
            "runs_considered": [c["path"].parent.name for c in top_candidates],
            "since_utc": window_start.isoformat(),
            "until_utc": now_utc.isoformat()
        },
        "totals": totals,
        "rows": rows
    }
    
    if refresh_hint:
        payload["refresh_hint"] = refresh_hint
        
    final_data = add_ssot_meta(payload, source_paths=source_inputs, notes="Cost Sensitivity Matrix SSOT.")
    return final_data


def main():
    try:
        data = build_cost_sensitivity_matrix()
    except Exception as e:
        # Fallback SSOT so consumers never hard crash
        import traceback
        now_iso = datetime.now(timezone.utc).isoformat()
        data = {
            "schema_version": "1.0",
            "producer_git_sha": "UNKNOWN",
            "generated_utc": now_iso,
            "source_inputs": [],
            "overall": "FAIL",
            "refresh_hint": f"Producer crashed: {str(e)}",
            "scenarios": [],
            "window": {},
            "totals": {"runs_seen": 0, "rows": 0, "ok": 0, "warn": 0, "unknown": 0},
            "rows": []
        }
    
    OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SSOT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"[OK] Cost Sensitivity Matrix generated > {OUTPUT_SSOT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
