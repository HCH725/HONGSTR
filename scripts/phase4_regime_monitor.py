#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).parent.parent
PHASE3_RESULTS = REPO / "reports/strategy_research/phase3/phase3_results.json"
STATE_DIR = REPO / "data/state"
REPORT_DIR = REPO / "reports/strategy_research/phase4"

def get_latest_backtest_summary():
    backtest_root = REPO / "data/backtests"
    if not backtest_root.exists():
        return None
    
    summaries = list(backtest_root.glob("**/summary.json"))
    if not summaries:
        return None
    
    # Sort by mtime
    summaries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return summaries[0]

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

def evaluate(current, thresholds):
    status = "OK"
    reasons = []
    
    curr_sharpe = current.get("sharpe", 0.0)
    curr_trades = current.get("trades_count", 0)
    curr_mdd = current.get("max_drawdown", 0.0)
    
    # 1. Sharpe Check
    s_warn = thresholds["sharpe"]["warn"]
    s_fail = thresholds["sharpe"]["fail"]
    
    if curr_sharpe < s_fail:
        status = "FAIL"
        reasons.append(f"Sharpe ({curr_sharpe:.3f}) < FAIL threshold ({s_fail:.3f})")
    elif curr_sharpe < s_warn:
        if status != "FAIL": status = "WARN"
        reasons.append(f"Sharpe ({curr_sharpe:.3f}) < WARN threshold ({s_warn:.3f})")
    
    # 2. Trade Count Gate
    t_gate = thresholds["trades"]["warn_gate"]
    if curr_trades < t_gate:
        if status != "FAIL": status = "WARN"
        reasons.append(f"Trade Count ({curr_trades}) < 50% of Phase 3 median ({t_gate:.0f}) - Possible regime shift or data gap")
    
    # 3. MDD Risk Check (MDD is negative)
    m_p80 = thresholds["mdd"]["p80"]
    m_p95 = thresholds["mdd"]["p95"]
    
    if curr_mdd < m_p95: # More negative than p95
        status = "FAIL"
        reasons.append(f"MDD ({curr_mdd:.2%}) < FAIL threshold ({m_p95:.2%}) - Extreme risk detected")
    elif curr_mdd < m_p80: # More negative than p80
        if status != "FAIL": status = "WARN"
        reasons.append(f"MDD ({curr_mdd:.2%}) < WARN threshold ({m_p80:.2%}) - Risk elevated")

    if not reasons:
        reasons.append("All metrics within Phase 3 comfort zone.")
        
    return status, reasons

def main():
    if not PHASE3_RESULTS.exists():
        print(f"Error: {PHASE3_RESULTS} not found.")
        sys.exit(0) # report_only, exit 0
        
    with open(PHASE3_RESULTS, "r") as f:
        phase3_data = json.load(f)
        
    thresholds = compute_thresholds(phase3_data)
    if not thresholds:
        print("Error: Could not compute thresholds from Phase 3 data.")
        sys.exit(0)
        
    latest_summary_p = get_latest_backtest_summary()
    if not latest_summary_p:
        print("Error: No backtest summary found.")
        sys.exit(0)
        
    with open(latest_summary_p, "r") as f:
        current_data = json.load(f)
        
    status, reasons = evaluate(current_data, thresholds)
    
    snapshot = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "overall": status,
        "reason": reasons,
        "phase3_baseline": {
            "oos_sharpe_median": thresholds["sharpe"]["median"],
            "p20": thresholds["sharpe"]["p20"],
            "p40": thresholds["sharpe"]["p40"],
            "trade_median": thresholds["trades"]["median"],
            "mdd_p80": thresholds["mdd"]["p80"]
        },
        "current": {
            "sharpe": current_data.get("sharpe"),
            "mdd": current_data.get("max_drawdown"),
            "return": current_data.get("total_return"),
            "trades": current_data.get("trades_count"),
            "summary_source": str(latest_summary_p.relative_to(REPO))
        },
        "suggestion": "Monitor regime shifts. If FAIL, consider re-optimizing parameters or manual pause (report_only)."
    }
    
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "regime_monitor_latest.json", "w") as f:
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
- Source Data: `{snapshot['current']['summary_source']}`

---
*Note: This is a report-only diagnostic. No automated actions were taken.*
"""
    
    with open(REPORT_DIR / "regime_monitor.md", "w") as f:
        f.write(report_md)
        
    print(f"Regime monitor finished with status: {status}")
    sys.exit(0)

if __name__ == "__main__":
    main()
