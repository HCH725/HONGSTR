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
    # Handle the fact that _ssot_meta might be missing or unreachable based on runtime
    def add_ssot_meta(payload: dict, source_paths=None, notes: str = "") -> dict:
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

OUTPUT_SSOT = REPO / "data/state/backtest_runs_index_latest.json"
BACKTESTS_DIR = REPO / "data/backtests"

def build_backtest_runs_index() -> Dict[str, Any]:
    now_utc = datetime.now(timezone.utc)
    lookback_days = 90
    window_start = now_utc - timedelta(days=lookback_days)
    max_rows = 200

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
        })

    # Sort descending by mtime and cap the max depth
    candidates.sort(key=lambda x: x["mtime"], reverse=True)
    top_candidates = candidates[:max_rows]

    totals = {
        "runs_found": len(candidates),
        "runs_indexed": 0,
        "parse_errors": 0,
        "missing_gate": 0,
        "missing_fields": 0
    }

    rows = []
    source_inputs = []
    
    for c in top_candidates:
        summary_path = c["path"]
        
        try:
            rel_path = summary_path.relative_to(REPO)
        except ValueError:
            rel_path = summary_path
            
        run_dir = summary_path.parent
        run_id = run_dir.name
        
        # safely extract run_date "YYYY-MM-DD" from parent hierarchy if applicable
        run_date = None
        try:
            parent_name = run_dir.parent.name
            if len(parent_name) == 10 and parent_name.count("-") == 2:
                # Basic validation
                datetime.strptime(parent_name, "%Y-%m-%d")
                run_date = parent_name
        except ValueError:
            pass
            
        source_inputs.append(str(rel_path))

        try:
            with open(summary_path, "r", encoding="utf-8") as f:
                s_data = json.load(f)
        except Exception:
            totals["parse_errors"] += 1
            continue

        totals["runs_indexed"] += 1
        
        # Flatten Strategy resolution (handle per_symbol variants cleanly without overinflating index row-counts).
        # We index purely on the explicit keys available.
        per_symbol = s_data.get("per_symbol", {})
        if per_symbol and isinstance(per_symbol, dict):
            # If multiple exist, we use the first to represent the bundle, or compile a generic note.
            # To keep index size controlled, we use the aggregated global stats typically sitting in the root.
            strat_name = s_data.get("strategy") or list(per_symbol.keys())[0] if per_symbol else "UNKNOWN"
            metrics_source = s_data
            if "sharpe" not in s_data and per_symbol:
                metrics_source = per_symbol[list(per_symbol.keys())[0]]
        else:
            strat_name = s_data.get("strategy") or "UNKNOWN"
            metrics_source = s_data

        ts_utc = metrics_source.get("timestamp") or metrics_source.get("ts_utc")
        timeframe = metrics_source.get("timeframe")
        regime = metrics_source.get("regime")
        
        metrics = {}
        missing_critical_fields = False
        for field, alias in [("sharpe", "sharpe"), ("max_drawdown", "mdd"), ("total_return", "ret"), ("trades_count", "trades")]:
            val = metrics_source.get(field)
            if val is None:
                val = metrics_source.get(alias)
            if val is not None:
                metrics[alias] = val
            else:
                missing_critical_fields = True
                
        if missing_critical_fields:
            totals["missing_fields"] += 1

        # Evaluate gate.json
        gate_path = run_dir / "gate.json"
        has_gate = False
        gate_status = "UNKNOWN"
        notes = None
        
        if gate_path.is_file():
            has_gate = True
            source_inputs.append(str(gate_path.relative_to(REPO) if str(REPO) in str(gate_path) else gate_path))
            try:
                with open(gate_path, "r", encoding="utf-8") as gf:
                    g_data = json.load(gf)
                    
                overall = g_data.get("overall") or g_data.get("results", {}).get("overall")
                
                if overall is not None:
                    if isinstance(overall, str):
                        gate_status = overall.upper()
                    elif isinstance(overall, dict):
                        gate_pass = overall.get("pass")
                        if gate_pass is True:
                            gate_status = "PASS"
                        elif gate_pass is False:
                            gate_status = "FAIL"
                else:
                    g_ok = g_data.get("ok")
                    g_pass = g_data.get("pass")
                    if g_ok is True or g_pass is True:
                        gate_status = "PASS"
                    elif g_ok is False or g_pass is False:
                        gate_status = "FAIL"
                    else:
                        notes = "unrecognized gate schema"
                        
            except Exception:
                gate_status = "UNKNOWN"
                notes = "parse error in gate.json"
        else:
            totals["missing_gate"] += 1

        rows.append({
            "run_id": run_id,
            "run_date": run_date,
            "summary_path": str(rel_path),
            "ts_utc": str(ts_utc) if ts_utc else None,
            "strategy": strat_name,
            "timeframe": str(timeframe) if timeframe else None,
            "regime": str(regime) if regime else None,
            "metrics": metrics,
            "has_gate": has_gate,
            "gate_status": gate_status,
            "notes": notes
        })

    # Producer health
    overall = "OK"
    refresh_hint = ""
    if totals["parse_errors"] > 0:
        overall = "WARN"
        refresh_hint = f"Encountered {totals['parse_errors']} unparsable summaries."
    if totals["runs_found"] == 0:
        overall = "WARN"
        refresh_hint = "0 valid backtest runs discovered in the 90 day window."

    payload = {
        "overall": overall,
        "window": {
            "lookback_days": lookback_days,
            "since_utc": window_start.isoformat(),
            "until_utc": now_utc.isoformat()
        },
        "totals": totals,
        "rows": rows
    }
    
    if refresh_hint:
        payload["refresh_hint"] = refresh_hint
        
    final_data = add_ssot_meta(payload, source_paths=list(set(source_inputs)), notes="Backtest Runs Index SSOT.")
    return final_data


def main():
    try:
        data = build_backtest_runs_index()
    except Exception as e:
        now_iso = datetime.now(timezone.utc).isoformat()
        data = {
            "schema_version": "1.0",
            "producer_git_sha": "UNKNOWN",
            "generated_utc": now_iso,
            "source_inputs": [],
            "overall": "FAIL",
            "refresh_hint": f"Producer execution crashed: {str(e)}",
            "window": {},
            "totals": {"runs_found": 0, "runs_indexed": 0, "parse_errors": 0, "missing_gate": 0, "missing_fields": 0},
            "rows": []
        }
    
    OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SSOT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # We truncate the absolute REPO bits for cleaner printing gracefully
    try:
        p_path = OUTPUT_SSOT.relative_to(REPO_ROOT)
    except Exception:
        p_path = OUTPUT_SSOT
    print(f"[OK] Backtest Runs Index generated > {p_path}")


if __name__ == "__main__":
    main()
