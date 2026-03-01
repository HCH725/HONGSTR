#!/usr/bin/env python3
"""
HONGSTR Overfit Governance SSOT (P1-1)
Provides an aggregated SSOT summarizing overfit/validation gates across recent backtest/research artifacts.
"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths
REPO = Path(__file__).parent.parent
REPO_ROOT = str(REPO.resolve())
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

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

OUTPUT_SSOT = REPO / "data/state/overfit_governance_latest.json"
BACKTESTS_DIR = REPO / "data/backtests"

WINDOW_DAYS = 7
MAX_RUNS = 5
MAX_ROWS = 50

# Valid codes we want to map to
REASON_CODES = {
    "OOS_FAIL", "WF_UNSTABLE", "COST_SENSITIVE", 
    "MDD_FAIL", "SHARPE_FAIL", "MISSING_METRIC", "PARSE_ERROR"
}

def _parse_gate_reason(reasons_list: list) -> list:
    """Map arbitrary internal reasons to the fixed SSOT schema roughly."""
    mapped = set()
    for r in reasons_list:
        r_up = str(r).upper()
        if "MDD" in r_up: mapped.add("MDD_FAIL")
        elif "SHARPE" in r_up: mapped.add("SHARPE_FAIL")
        elif "COST" in r_up or "FEE" in r_up: mapped.add("COST_SENSITIVE")
        elif "OOS" in r_up: mapped.add("OOS_FAIL")
        elif "WF" in r_up or "WALK" in r_up: mapped.add("WF_UNSTABLE")
    return list(mapped) if mapped else ["OOS_FAIL"]  # generic default if string doesn't match keys


def process_run(run_dir: Path) -> list:
    """Process a single run directory, returning a list of row payload objects."""
    evidence_paths = []
    
    # 1. Gather file artifacts gracefully
    summary_path = run_dir / "summary.json"
    gate_path = run_dir / "gate.json"
    selection_path = run_dir / "selection.json"
    leaderboard_path = run_dir / "leaderboard.json"

    if gate_path.exists(): evidence_paths.append(gate_path)
    if summary_path.exists(): evidence_paths.append(summary_path)
    if selection_path.exists(): evidence_paths.append(selection_path)
    if leaderboard_path.exists(): evidence_paths.append(leaderboard_path)
    
    run_id = run_dir.name
    evidence_payload = [{"path": str(ep.relative_to(REPO))} for ep in evidence_paths]
    
    # Missing crucial metrics = UNKNOWN
    if not gate_path.exists():
        return [{
            "id": run_id,
            "strategy": "UNKNOWN",
            "status": "UNKNOWN",
            "reasons": ["MISSING_METRIC"],
            "evidence": evidence_payload
        }]

    # 2. Parse Gate.json Structure Robustly
    try:
        raw_b = gate_path.read_bytes()
        gate_data = json.loads(raw_b.decode("utf-8"))
    except Exception as e:
        return [{
            "id": run_id,
            "strategy": "UNKNOWN",
            "status": "UNKNOWN",
            "reasons": ["PARSE_ERROR"],
            "evidence": evidence_payload
        }]
    
    rows = []
    # Identify dynamic schema paths for strategy-level objects
    candidates = {}
    if "results" in gate_data and "by_regime" in gate_data["results"]:
        # Structure A (Benchmark suite typically produces this)
        overall_pass = gate_data.get("results", {}).get("overall", {}).get("pass", False)
        cand_id = f"{run_id}_benchmark"
        
        # Determine aggregate reasons for benchmark
        agg_reasons = []
        if not overall_pass:
            for k, v in gate_data["results"]["by_regime"].items():
                if not v.get("pass", False):
                    agg_reasons.extend(v.get("reasons", []))
                    
        candidates[cand_id] = {
            "strategy": "benchmark_portfolio",
            "pass": overall_pass,
            "reasons": _parse_gate_reason(agg_reasons) if not overall_pass else []
        }
    elif "candidates" in gate_data:
        # Structure B (Strategy Pool Update style)
        for cand_id, cand_data in gate_data["candidates"].items():
            candidates[cand_id] = {
                "strategy": cand_data.get("strategy_id", cand_id),
                "pass": cand_data.get("pass", False),
                "reasons": _parse_gate_reason(cand_data.get("reasons", []))
            }

    # 3. Fallback Row Generation (If no strategy configs exist in JSON structurally)
    if not candidates:
        return [{
            "id": run_id,
            "strategy": "UNKNOWN",
            "status": "UNKNOWN",
            "reasons": ["MISSING_METRIC"],
            "evidence": evidence_payload
        }]
        
    for cid, cdata in candidates.items():
        st = "PASS" if cdata["pass"] else "FAIL"
        rows.append({
            "id": cid,
            "strategy": cdata["strategy"],
            "status": st,
            "reasons": cdata["reasons"],
            "evidence": evidence_payload
        })
        
    return rows


def main():
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=WINDOW_DAYS)
    
    # 1. Discovery phase
    candidates = []
    if BACKTESTS_DIR.exists():
        for summary_path in BACKTESTS_DIR.rglob("summary.json"):
            st = summary_path.stat()
            mtime = datetime.fromtimestamp(st.st_mtime, timezone.utc)
            if mtime >= window_start:
                candidates.append((mtime, summary_path.parent))
                
    # Sort DESC and limit to N
    candidates.sort(key=lambda x: x[0], reverse=True)
    top_runs = [p for m, p in candidates[:MAX_RUNS]]
    
    # 2. Processing Phase
    totals = {
        "candidates_seen": 0,
        "pass": 0,
        "warn": 0,
        "fail": 0,
        "unknown": 0
    }
    rows = []
    runs_considered = []
    source_inputs = []
    
    for run_dir in top_runs:
        runs_considered.append(run_dir.name)
        
        # Link source inputs representing the run scope (for SSOT meta)
        sm_path = run_dir / "summary.json"
        if sm_path.exists():
            st = sm_path.stat()
            source_inputs.append({
                "path": str(sm_path.relative_to(REPO)),
                "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                "size_bytes": st.st_size,
                "fingerprint": "run_summary"
            })
            
        run_rows = process_run(run_dir)
        for r in run_rows:
            totals["candidates_seen"] += 1
            st_key = r["status"].lower()
            if st_key in totals:
                totals[st_key] += 1
            rows.append(r)
            
    # Cap rows to prevent SSOT payload explosion
    if len(rows) > MAX_ROWS:
        rows = rows[:MAX_ROWS]
        
    # 3. Aggregation and System Pipeline Health
    # Note: overall refers to the pipeline execution, not the gate outcome!
    overall = "OK" 
    refresh_hint = ""
    
    if not top_runs:
        overall = "WARN"
        refresh_hint = f"No backtests found in the last {WINDOW_DAYS} days."
    elif totals["unknown"] > 0:
        # If SOME files parsed but threw exceptions / missing metrics, flag pipeline health
        overall = "WARN"
        refresh_hint = f"Some runs ({totals['unknown']}) threw PARSE_ERROR or MISSING_METRIC."

    payload = {
        "overall": overall,
        "window": {
            "lookback_days": WINDOW_DAYS,
            "since_utc": window_start.isoformat(),
            "until_utc": now_utc.isoformat(),
            "runs_considered": runs_considered
        },
        "totals": totals,
        "rows": rows,
        "refresh_hint": refresh_hint
    }
    
    # 4. SSOT Write
    meta = add_ssot_meta(payload, notes="Overfit Governance audit.")
    
    # Inject aggregated dynamic source_inputs carefully. SSOT Meta prepends static ones.
    for si in source_inputs:
        # Avoid duplicate static injection if path matches
        if not any(x["path"] == si["path"] for x in meta["source_inputs"]):
            meta["source_inputs"].insert(0, si)
            
    OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SSOT, "w") as f:
        json.dump(meta, f, indent=2)
        
    print(f"[{overall}] Overfit Governance generated > {OUTPUT_SSOT.relative_to(REPO)}")
        
if __name__ == "__main__":
    main()
