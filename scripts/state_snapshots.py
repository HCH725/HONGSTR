#!/usr/bin/env python3
"""
scripts/state_snapshots.py
Reads large JSONL state files and produces small, structured JSON snapshots for web dashboards.
Strictly Read-Only on core. Stability-first (exit 0).
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STATE_DIR = Path("data/state")

def read_jsonl(path: Path):
    records = []
    if not path.exists():
        return records
    try:
        with open(path, "r") as f:
            for line in f:
                ln = line.strip()
                if ln:
                    try:
                        records.append(json.loads(ln))
                    except Exception:
                        pass
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
    return records

def read_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
        return None

def write_json(path: Path, data: dict):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to write snapshot {path}: {e}")

def main():
    now_utc_obj = datetime.now(timezone.utc)
    now_utc = now_utc_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ts = time.time()

    # 1. Coverage Latest
    cov_recs = read_jsonl(STATE_DIR / "coverage_table.jsonl")
    latest_map = {}
    for r in cov_recs:
        key_obj = r.get("coverage_key", {})
        sym = key_obj.get("symbol", "UNKNOWN")
        tf = key_obj.get("timeframe", "UNKNOWN")
        regime = key_obj.get("regime", "UNKNOWN")
        mkey = f"{sym}_{tf}_{regime}"
        latest_map[mkey] = r

    write_json(STATE_DIR / "coverage_latest.json", latest_map)

    # 2. Coverage Summary
    cov_summary = {
        "count": len(cov_recs),
        "pass_rate": 0,
        "avg_sharpe": 0.0,
        "avg_mdd": 0.0,
        "last_updated_utc": now_utc
    }
    passes = 0
    total_sharpe = 0.0
    for r in latest_map.values():
        status = r.get("status", "")
        if status == "DONE":
            passes += 1
        # best-effort extract sharpe from notes
        notes = r.get("notes", "")
        if "Sharpe:" in notes:
            try:
                parts = notes.split("Sharpe:")[1].split(",")
                val = float(parts[0].strip())
                total_sharpe += val
            except:
                pass
    
    if len(latest_map) > 0:
        cov_summary["pass_rate"] = round(passes / len(latest_map), 2)
        cov_summary["avg_sharpe"] = round(total_sharpe / len(latest_map), 2)
    
    write_json(STATE_DIR / "coverage_summary.json", cov_summary)

    # 3. Strategy Pool Summary
    pool_data = read_json(STATE_DIR / "strategy_pool.json") or {}
    candidates = pool_data.get("candidates", [])
    promoted = pool_data.get("promoted", [])
    demoted = pool_data.get("demoted", [])

    leaderboard = [
        {
            "id": c.get("strategy_id", "unknown"),
            "score": c.get("last_score", 0),
            "sharpe": c.get("last_oos_metrics", {}).get("sharpe", 0),
            "return": c.get("last_oos_metrics", {}).get("return", 0),
            "mdd": c.get("last_oos_metrics", {}).get("mdd", 0),
        }
        for c in candidates
    ]
    leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)[:10]

    pool_summary = {
        "counts": {
            "candidates": len(candidates),
            "promoted": len(promoted),
            "demoted": len(demoted)
        },
        "leaderboard": leaderboard,
        "last_updated_utc": now_utc
    }

    write_json(STATE_DIR / "strategy_pool_summary.json", pool_summary)

    # 4. Regime Monitor Summary
    regime_data = read_json(STATE_DIR / "regime_monitor_latest.json")
    if regime_data:
        regime_summary = {
            "status": regime_data.get("overall", "UNKNOWN"),
            "updated_utc": regime_data.get("ts_utc"),
            "key_metrics": {
                "sharpe": regime_data.get("current", {}).get("sharpe"),
                "mdd": regime_data.get("current", {}).get("mdd"),
                "trades": regime_data.get("current", {}).get("trades"),
            },
            "thresholds": {
                "sharpe_warn": regime_data.get("phase3_baseline", {}).get("p40"), # approximation
                "sharpe_fail": regime_data.get("phase3_baseline", {}).get("p20"),
            },
            "reasons": regime_data.get("reason", []),
            "sources": [regime_data.get("current", {}).get("summary_source")]
        }
        write_json(STATE_DIR / "regime_monitor_summary.json", regime_summary)
    else:
        write_json(STATE_DIR / "regime_monitor_summary.json", {"status": "UNKNOWN", "last_updated_utc": now_utc})

    # 5. Data Freshness 3x3
    freshness_matrix = []
    thresholds = {"ok_h": 12.0, "warn_h": 48.0}
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframes = ["1m", "1h", "4h"]

    for sym in symbols:
        for tf in timeframes:
            # Consistent with tg_cp: read only from derived
            p = Path(".") / f"data/derived/{sym}/{tf}/klines.jsonl"
            
            age_h = None
            reason = None
            source = str(p.relative_to(Path("."))) if p.exists() else None
            
            if p.exists():
                try:
                    age_h = (now_ts - p.stat().st_mtime) / 3600.0
                except Exception as e:
                    reason = f"stat_error: {str(e)}"
            else:
                reason = "missing_source"
            
            status = "FAIL"
            if reason:
                status = "FAIL"
            elif age_h is None:
                status = "FAIL"
                reason = "unknown_age"
            elif age_h <= thresholds["ok_h"]:
                status = "OK"
            elif age_h <= thresholds["warn_h"]:
                status = "WARN"
                reason = f"exceeds 12h ({age_h:.1f}h)"
            else:
                status = "FAIL"
                reason = f"exceeds 48h ({age_h:.1f}h)"
            
            freshness_matrix.append({
                "symbol": sym,
                "tf": tf,
                "age_h": round(age_h, 1) if age_h is not None else None,
                "status": status,
                "source": source,
                "reason": reason
            })

    freshness_table = {
        "generated_utc": now_utc,
        "thresholds": thresholds,
        "rows": freshness_matrix 
    }
    write_json(STATE_DIR / "freshness_table.json", freshness_table)

    # 6. Execution Mode Snapshot
    execution_mode = {
        "mode": os.getenv("EXECUTION_MODE", "unknown"),
        "last_updated_utc": now_utc
    }
    write_json(STATE_DIR / "execution_mode.json", execution_mode)

    # 7. Services Heartbeat Snapshot
    services = {
        "dashboard": "logs/launchd_dashboard.out.log",
        "realtime": "logs/realtime_ws.log",
        "tg_cp": "logs/launchd_tg_cp.out.log",
        "etl": "logs/launchd_daily_etl.out.log",
        "backtest": "logs/launchd_daily_backtest.out.log",
        "poller": "logs/launchd_research_poller.out.log"
    }
    heartbeat = {
        "generated_utc": now_utc,
        "services": {}
    }
    for svc_name, log_path_str in services.items():
        lp = Path(log_path_str)
        status = "UNKNOWN"
        age_h = None
        last_ts = None
        if lp.exists():
            last_ts = lp.stat().st_mtime
            age_h = (now_ts - last_ts) / 3600.0
            # Heuristic: < 1h is ALIVE, < 24h is IDLE, else DEAD (for continuous services)
            if age_h < 1.0:
                status = "ALIVE"
            elif age_h < 24.0:
                status = "IDLE"
            else:
                status = "DEAD"
        
        heartbeat["services"][svc_name] = {
            "status": status,
            "log_path": log_path_str,
            "age_h": round(age_h, 2) if age_h is not None else None,
            "last_heartbeat_utc": datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if last_ts else None
        }
    
    write_json(STATE_DIR / "services_heartbeat.json", heartbeat)

    logging.info("Snapshots successfully written to data/state/")

if __name__ == "__main__":
    main()
    exit(0)
