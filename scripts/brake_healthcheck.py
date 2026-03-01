#!/usr/bin/env python3
"""
HONGSTR Brake Healthcheck (R3-C)
Verifies existence and recency of critical system artifacts (brakes).
Usage: ./scripts/brake_healthcheck.py
Env: BRAKE_HC_STRICT=1 (Exit 1 on any FAIL)
"""

import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone

try:
    from scripts._ssot_meta import add_ssot_meta
except ImportError:
    import sys
    sys.path.append(str(Path(__file__).parent))
    from _ssot_meta import add_ssot_meta


# Configuration
FRESHNESS_PATH = "data/state/freshness_table.json"
REGIME_PATH_CANDIDATES = (
    "reports/state_atomic/regime_monitor_latest.json",
)
HEALTH_JSON_PATH = "reports/state_atomic/brake_health_latest.json"

FRESHNESS_MAX_AGE_SEC = 24 * 3600  # 24h
REGIME_MAX_AGE_SEC = 12 * 3600     # 12h

STRICT_MODE = os.getenv("BRAKE_HC_STRICT", "0") == "1"

# ANSI Colors
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_RESET = "\033[0m"


def pick_existing_path(candidates):
    for c in candidates:
        if Path(c).exists():
            return c
    # Fallback to the first candidate for deterministic messaging.
    return candidates[0]

def get_latest_run_dir():
    try:
        # Try helper script first
        res = subprocess.run(["bash", "scripts/get_latest_completed_dir.sh"], 
                             capture_output=True, text=True, check=True)
        return Path(res.stdout.strip())
    except:
        # Fallback manual scan
        root = Path("data/backtests")
        if not root.exists():
            return None
        summaries = sorted(root.glob("*/*/summary.json"), key=os.path.getmtime, reverse=True)
        if summaries:
            return summaries[0].parent
        return None

def check_file(path, max_age_sec=None):
    p = Path(path)
    if not p.exists():
        return "FAIL", "MISSING", None, None

    
    mtime = p.stat().st_mtime
    age_sec = time.time() - mtime
    
    if max_age_sec and age_sec > max_age_sec:
        lag_h = age_sec/3600.0
        return "WARN", f"STALE (lag={lag_h:.1f}h > {max_age_sec/3600.0:.1f}h)", mtime, None
    
    # Try parse JSON
    try:
        with open(p, "r") as f:
            data = json.load(f)
            ts_utc = data.get("generated_utc") or data.get("timestamp") or data.get("ts_utc") or data.get("updated_at_utc")
    except Exception as e:
        return "FAIL", f"CORRUPT ({str(e)[:20]})", mtime, None
        
    return "OK", "Fresh", mtime, ts_utc

def main():
    results = []
    any_fail = False
    reasons = set()
    evidence = []

    def _add_evidence(label, path, note, ts_utc=None):
        if Path(path).exists():
            ev = {"label": label, "path": str(path), "note": note}
            if ts_utc:
                ev["ts_utc"] = ts_utc
            evidence.append(ev)

    # 1. Freshness Table
    status, note, mtime, ts_utc = check_file(FRESHNESS_PATH, FRESHNESS_MAX_AGE_SEC)
    results.append({"item": "Freshness Table", "status": status, "note": note, "path": FRESHNESS_PATH})
    if status != "OK":
        any_fail = True
        reasons.add("STALE_DATA")
        _add_evidence("Freshness Table", FRESHNESS_PATH, note, ts_utc)

    # 2. Regime Monitor
    regime_path = pick_existing_path(REGIME_PATH_CANDIDATES)
    status, note, mtime, ts_utc = check_file(regime_path, REGIME_MAX_AGE_SEC)
    results.append({"item": "Regime Monitor", "status": status, "note": note, "path": regime_path})
    if status != "OK":
        any_fail = True
        reasons.add("REGIME_FAIL")
        _add_evidence("Regime Monitor", regime_path, note, ts_utc)

    # 3. Latest Backtest Artifacts
    run_dir = get_latest_run_dir()
    if not run_dir:
        results.append({"item": "Latest Backtest", "status": "FAIL", "note": "NO_RUNS_FOUND", "path": "data/backtests/"})
        any_fail = True
        reasons.add("COVERAGE_GAP")
    else:
        for art in ["summary.json", "selection.json", "gate.json"]:
            path = run_dir / art
            status, note, mtime, ts_utc = check_file(path)
            results.append({"item": f"Backtest {art}", "status": status, "note": note, "path": str(path)})
            if status != "OK":
                any_fail = True
                reasons.add("COVERAGE_GAP")
                _add_evidence(f"Backtest {art}", path, note, ts_utc)

        # Drawdown limit check specifically
        summary_path = run_dir / "summary.json"
        if summary_path.exists():
            try:
                with open(summary_path, "r") as f:
                    summ = json.load(f)
                    mdd = summ.get("max_drawdown")
                    if mdd is not None and float(mdd) <= -0.25: # hardcoded check
                        reasons.add("DD_LIMIT")
                        _add_evidence("Max Drawdown", summary_path, f"MDD={mdd} breached -25% limit", summ.get("timestamp"))
            except Exception:
                pass


    # Print Table
    print("\n=== HONGSTR Brake Healthcheck ===")
    print(f"{'Item':<25} | {'Status':<6} | {'Note':<35} | {'Path'}")
    print("-" * 100)
    for r in results:
        color = C_RESET
        if r["status"] == "OK": color = C_GREEN
        elif r["status"] == "WARN": color = C_YELLOW
        elif r["status"] == "FAIL": color = C_RED
        
        print(f"{r['item']:<25} | {color}{r['status']:<6}{C_RESET} | {r['note']:<35} | {r['path']}")

    # Build recommendations
    sops = {
        "STALE_DATA": "資料庫或 ETL 延遲：請檢查 daily_etl / realtime_ws 服務運行狀態，或查看 freshness_table 以確認落後的幣種/時區。",
        "COVERAGE_GAP": "回測覆蓋率異常或缺失：請手動檢查最近一次 bash scripts/run_and_verify.sh 執行日誌，確保 selection/ summary 生成完整。",
        "REGIME_FAIL": "市場狀態切換失效或遺失：檢查 phase4_regime_monitor.py 是否正常產生 output。",
        "DD_LIMIT": "策略觸發最大回撤 (MDD) 熔斷：系統已停止進入新部位，請進入 regime_slice 檢視策略是否失效，重新評估風險模型。",
        "LOSS_STREAK": "系統遇到連續虧損閥值：建議手動暫停高頻/均值回歸策略",
        "UNKNOWN": "系統處於未知異常狀態或檔案損毀，需要工程師介入盤查 Log。"
    }
    
    breach_reason_codes = list(reasons) if reasons else []
    recommended_actions = [sops[c] for c in breach_reason_codes if c in sops]

    # Write JSON
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "overall_fail": any_fail,
        "results": results,
        "strict_mode": STRICT_MODE,
        "breach_reason_codes": breach_reason_codes,
        "evidence": evidence,
        "recommended_actions": recommended_actions
    }
    
    try:
        os.makedirs(os.path.dirname(HEALTH_JSON_PATH), exist_ok=True)
        with open(HEALTH_JSON_PATH, "w") as f:
            json.dump(add_ssot_meta(summary, notes="Standard Brake Evidence Pack generated via brake_healthcheck"), f, indent=2)
        print(f"\nSummary written to: {HEALTH_JSON_PATH}")
    except Exception as e:
        print(f"\nFailed to write JSON summary: {e}")

    # Exit Logic
    if any_fail and STRICT_MODE:
        print(f"\n{C_RED}STRICT MODE FAIL: System health degraded.{C_RESET}")
        exit(1)
    
    print(f"\n{C_GREEN}Healthcheck complete.{C_RESET}")

if __name__ == "__main__":
    main()
