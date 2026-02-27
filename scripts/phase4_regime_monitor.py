#!/usr/bin/env python3
import json
import hashlib
import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).parent.parent
PHASE3_RESULTS = REPO / "reports/strategy_research/phase3/phase3_results.json"
ATOMIC_STATE_DIR = REPO / "reports/state_atomic"
REPORT_DIR = REPO / "reports/strategy_research/phase4"
THRESHOLD_POLICY_VERSION = "phase4_regime_monitor.thresholds.v1"

def resolve_latest_run():
    """
    Search for the latest 'Full Run' (containing both selection.json and summary.json).
    Fallback to the latest 'Fragment Run' (any summary.json) if no Full Run exists.
    """
    backtest_root = REPO / "data/backtests"
    if not backtest_root.exists():
        return None, None, "no_data"
    
    all_summaries = list(backtest_root.glob("**/summary.json"))
    if not all_summaries:
        return None, None, "no_summary_found"
    
    # Sort all summaries by mtime to find the latest overall
    all_summaries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    # 1. Search for a Full Run
    for summary_p in all_summaries:
        run_dir = summary_p.parent
        if (run_dir / "selection.json").exists():
            return run_dir, summary_p, "full_run"
            
    # 2. Fallback to the latest fragment run
    latest_fragment = all_summaries[0]
    return latest_fragment.parent, latest_fragment, "fallback_fragment"

def compute_thresholds(phase3_data):
    walks = phase3_data.get("walks", [])
    if not walks:
        return None
    
    sharpes = [w["sharpe"] for w in walks]
    mdds = [w["mdd"] for w in walks]
    trades = [w["trades"] for w in walks]
    
    sharpe_median = np.median(sharpes)
    sharpe_iqr = np.percentile(sharpes, 75) - np.percentile(sharpes, 25)
    sharpe_p20 = np.percentile(sharpes, 20)
    sharpe_p40 = np.percentile(sharpes, 40)
    
    trade_median = np.median(trades)
    
    # MDD is negative, so p95 is the most negative (worst risk)
    mdd_p80 = np.percentile(mdds, 20) # 20th percentile is more negative than 80th
    mdd_p95 = np.percentile(mdds, 5)  # 5th percentile is the extreme tail risk
    
    return {
        "sharpe": {
            "median": sharpe_median,
            "iqr": sharpe_iqr,
            "p20": sharpe_p20,
            "p40": sharpe_p40,
            "warn": sharpe_median - 0.5 * sharpe_iqr if sharpe_iqr > 0 else sharpe_p40,
            "fail": sharpe_median - 1.0 * sharpe_iqr if sharpe_iqr > 0 else sharpe_p20
        },
        "trades": {
            "median": trade_median,
            "warn_gate": trade_median * 0.5
        },
        "mdd": {
            "p80": mdd_p80,
            "p95": mdd_p95
        }
    }

def compute_threshold_policy_sha(raw_bytes):
    digest = hashlib.sha256()
    digest.update(THRESHOLD_POLICY_VERSION.encode("utf-8"))
    digest.update(b"\n")
    digest.update(raw_bytes)
    return digest.hexdigest()


def _severity_rank(level):
    if level == "FAIL":
        return 2
    if level == "WARN":
        return 1
    return 0


def evaluate(current, thresholds):
    status = "OK"
    reason_events = []
    order_counter = 0

    try:
        curr_sharpe = float(current.get("sharpe", 0.0))
    except Exception:
        curr_sharpe = 0.0
    try:
        curr_trades = int(float(current.get("trades_count", 0)))
    except Exception:
        curr_trades = 0
    try:
        curr_mdd = float(current.get("max_drawdown", 0.0))
    except Exception:
        curr_mdd = 0.0

    def add_event(level, message, metric, threshold_value, observed_value, comparator, rationale):
        nonlocal status, order_counter
        if level == "FAIL":
            status = "FAIL"
        elif status != "FAIL":
            status = "WARN"
        reason_events.append(
            {
                "level": level,
                "message": message,
                "metric": metric,
                "threshold_value": threshold_value,
                "observed_value": observed_value,
                "comparator": comparator,
                "rationale": rationale,
                "order": order_counter,
            }
        )
        order_counter += 1

    # 1. Sharpe Check
    s_warn = thresholds["sharpe"]["warn"]
    s_fail = thresholds["sharpe"]["fail"]

    if curr_sharpe < s_fail:
        add_event(
            "FAIL",
            f"Sharpe ({curr_sharpe:.3f}) < FAIL threshold ({s_fail:.3f})",
            "sharpe",
            s_fail,
            curr_sharpe,
            "<",
            "Current OOS Sharpe dropped below FAIL line derived from Phase 3 distribution.",
        )
    elif curr_sharpe < s_warn:
        add_event(
            "WARN",
            f"Sharpe ({curr_sharpe:.3f}) < WARN threshold ({s_warn:.3f})",
            "sharpe",
            s_warn,
            curr_sharpe,
            "<",
            "Current OOS Sharpe slipped below WARN line from Phase 3 IQR baseline.",
        )

    # 2. Trade Count Gate
    t_gate = thresholds["trades"]["warn_gate"]
    if curr_trades < t_gate:
        add_event(
            "WARN",
            f"Trade Count ({curr_trades}) < 50% of Phase 3 median ({t_gate:.0f}) - Possible regime shift or data gap",
            "trades_count",
            t_gate,
            curr_trades,
            "<",
            "Trade frequency is below half of Phase 3 median; could indicate data gap or market regime shift.",
        )

    # 3. MDD Risk Check (MDD is negative)
    m_p80 = thresholds["mdd"]["p80"]
    m_p95 = thresholds["mdd"]["p95"]

    if curr_mdd < m_p95: # More negative than p95
        add_event(
            "FAIL",
            f"MDD ({curr_mdd:.2%}) < FAIL threshold ({m_p95:.2%}) - Extreme risk detected",
            "max_drawdown",
            m_p95,
            curr_mdd,
            "<",
            "Max drawdown breached the extreme (p95 tail) risk threshold from Phase 3.",
        )
    elif curr_mdd < m_p80: # More negative than p80
        add_event(
            "WARN",
            f"MDD ({curr_mdd:.2%}) < WARN threshold ({m_p80:.2%}) - Risk elevated",
            "max_drawdown",
            m_p80,
            curr_mdd,
            "<",
            "Max drawdown is worse than the elevated-risk (p80) threshold from Phase 3.",
        )

    if not reason_events:
        return status, ["All metrics within Phase 3 comfort zone."], None

    sorted_events = sorted(reason_events, key=lambda r: (-_severity_rank(r["level"]), r["order"]))
    reasons = [event["message"] for event in sorted_events]
    primary = sorted_events[0]
    primary_threshold = {
        "metric": primary["metric"],
        "level": primary["level"],
        "threshold_value": primary["threshold_value"],
        "observed_value": primary["observed_value"],
        "comparator": primary["comparator"],
        "rationale": primary["rationale"],
    }
    return status, reasons, primary_threshold
 
def main():
    if not PHASE3_RESULTS.exists():
        print(f"Error: {PHASE3_RESULTS} not found.")
        sys.exit(0) # report_only, exit 0

    phase3_raw = PHASE3_RESULTS.read_bytes()
    with open(PHASE3_RESULTS, "r") as f:
        phase3_data = json.load(f)
    threshold_policy_sha = compute_threshold_policy_sha(phase3_raw)
    threshold_source_path = str(PHASE3_RESULTS.relative_to(REPO))
        
    thresholds = compute_thresholds(phase3_data)
    if not thresholds:
        print("Error: Could not compute thresholds from Phase 3 data.")
        sys.exit(0)
        
    latest_run_dir, latest_summary_p, source_reason = resolve_latest_run()
    if not latest_summary_p:
        print(f"Error: {source_reason}")
        sys.exit(0)
        
    with open(latest_summary_p, "r") as f:
        current_data = json.load(f)

    status, reasons, primary_threshold = evaluate(current_data, thresholds)

    threshold_value = None
    threshold_metric = None
    threshold_level = "OK"
    threshold_comparator = None
    threshold_observed_value = None
    threshold_rationale = "All metrics within Phase 3 comfort zone; no threshold breach."
    if isinstance(primary_threshold, dict):
        threshold_value = primary_threshold.get("threshold_value")
        threshold_metric = primary_threshold.get("metric")
        threshold_level = primary_threshold.get("level") or "WARN"
        threshold_comparator = primary_threshold.get("comparator")
        threshold_observed_value = primary_threshold.get("observed_value")
        threshold_rationale = primary_threshold.get("rationale") or threshold_rationale
    
    snapshot = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall": status,
        "reason": reasons,
        "threshold_value": threshold_value,
        "threshold_metric": threshold_metric,
        "threshold_level": threshold_level,
        "threshold_comparator": threshold_comparator,
        "threshold_observed_value": threshold_observed_value,
        "threshold_source_path": threshold_source_path,
        "threshold_policy_sha": threshold_policy_sha,
        "threshold_policy_version": THRESHOLD_POLICY_VERSION,
        "threshold_rationale": threshold_rationale,
        "phase3_baseline": {
            "oos_sharpe_median": thresholds["sharpe"]["median"],
            "p20": thresholds["sharpe"]["p20"],
            "p40": thresholds["sharpe"]["p40"],
            "trade_median": thresholds["trades"]["median"],
            "mdd_p80": thresholds["mdd"]["p80"]
        },
        "current": {
            "sharpe": current_data.get("sharpe", 0.0),
            "mdd": current_data.get("max_drawdown", 0.0),
            "return": current_data.get("total_return", 0.0),
            "trades": current_data.get("trades_count", 0),
            "run_dir": str(latest_run_dir.relative_to(REPO)) if latest_run_dir else "N/A",
            "summary_path": str(latest_summary_p.relative_to(REPO)) if latest_summary_p else "N/A",
            "source_reason": source_reason
        },
        "suggestion": "Monitor regime shifts. If FAIL, consider re-optimizing parameters or manual pause (report_only)."
    }
    
    ATOMIC_STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_regime_path = ATOMIC_STATE_DIR / "regime_monitor_latest.json"
    with open(atomic_regime_path, "w") as f:
        json.dump(snapshot, f, indent=2)
        
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    
    report_md = f"""# Strategy Regime Monitor Report
Generated: {snapshot['ts_utc']}

## Overall Status: {status}

### What we see
- **Current Sharpe**: {snapshot['current']['sharpe']:.3f} (Threshold: WARN<{thresholds['sharpe']['warn']:.3f}, FAIL<{thresholds['sharpe']['fail']:.3f})
- **Current MDD**: {snapshot['current']['mdd']:.2%} (Baseline p80: {thresholds['mdd']['p80']:.2%})
- **Trade Count**: {snapshot['current']['trades']} (Median: {thresholds['trades']['median']:.0f}, Warn Gate: {thresholds['trades']['warn_gate']:.0f})

### Why it matters
{" ".join(reasons)}

### What to do next (manual)
- {snapshot['suggestion']}
- Source Data: `{snapshot['current']['summary_path']}` ({snapshot['current']['source_reason']})

---
*Note: This is a report-only diagnostic. No automated actions were taken.*
"""
    
    with open(REPORT_DIR / "regime_monitor.md", "w") as f:
        f.write(report_md)
        
    print(f"Regime monitor finished with status: {status}")
    print(f"Atomic output: {atomic_regime_path.relative_to(REPO)}")
    sys.exit(0)

if __name__ == "__main__":
    main()
