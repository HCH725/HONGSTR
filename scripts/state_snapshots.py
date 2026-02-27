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
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STATE_DIR = Path("data/state")
ATOMIC_STATE_DIR = Path("reports/state_atomic")
ATOMIC_COVERAGE_TABLE = ATOMIC_STATE_DIR / "coverage_table.jsonl"
ATOMIC_REGIME_MONITOR = ATOMIC_STATE_DIR / "regime_monitor_latest.json"
ATOMIC_BRAKE_HEALTH = ATOMIC_STATE_DIR / "brake_health_latest.json"
DEFAULT_FRESHNESS_PROFILE = "realtime"
FRESHNESS_THRESHOLDS = {
    "realtime": {"ok_h": 0.1, "warn_h": 0.25, "fail_h": 1.0},
    "backtest": {"ok_h": 26.0, "warn_h": 50.0, "fail_h": 72.0},
}
FRESHNESS_ROW_KEYS = ("symbol", "tf", "profile", "age_h", "status", "source", "reason")


def _normalize_simple_status(status_raw):
    status = str(status_raw or "").upper().strip()
    if status in {"OK", "PASS", "WARN", "FAIL", "UNKNOWN"}:
        return status
    return "UNKNOWN"


def _freshness_profile_from_source(source: Optional[str], default_profile: str = DEFAULT_FRESHNESS_PROFILE) -> str:
    src = str(source or "").replace("\\", "/")
    if "data/realtime" in src:
        return "realtime"
    if "data/derived" in src and src.endswith("klines.jsonl"):
        return "backtest"
    return default_profile


def _evaluate_freshness_status(age_h: Optional[float], profile: str, source_error: Optional[str] = None) -> tuple[str, Optional[str]]:
    """
    SSOT freshness evaluation.
    FAIL is reserved for missing/unreadable source; stale snapshots degrade to WARN.
    This preserves non-blocking SSOT behavior while exposing profile-specific thresholds.
    """
    profile_key = profile if profile in FRESHNESS_THRESHOLDS else DEFAULT_FRESHNESS_PROFILE
    thresholds = FRESHNESS_THRESHOLDS[profile_key]

    if source_error:
        return "FAIL", source_error
    if age_h is None:
        return "FAIL", "unknown_age"
    if age_h <= thresholds["ok_h"]:
        return "OK", None
    if age_h <= thresholds["warn_h"]:
        return "WARN", f"exceeds {thresholds['ok_h']:.2f}h ({age_h:.1f}h)"
    if age_h <= thresholds["fail_h"]:
        return "WARN", f"exceeds {thresholds['warn_h']:.2f}h ({age_h:.1f}h)"
    return "WARN", f"exceeds {thresholds['fail_h']:.2f}h ({age_h:.1f}h)"


def _canonicalize_freshness_row(
    symbol: object,
    tf: object,
    profile: Optional[str],
    age_h: Optional[float],
    status: object,
    source: Optional[str],
    reason: Optional[str],
) -> dict:
    """
    Enforce deterministic row schema for ops-grade freshness output.
    Keys and value types are normalized to avoid shape drift across runs.
    """
    symbol_norm = str(symbol or "UNKNOWN").strip() or "UNKNOWN"
    tf_norm = str(tf or "UNKNOWN").strip() or "UNKNOWN"

    profile_norm = str(profile or DEFAULT_FRESHNESS_PROFILE).strip().lower()
    if profile_norm not in FRESHNESS_THRESHOLDS:
        profile_norm = DEFAULT_FRESHNESS_PROFILE

    source_norm = str(source or "").replace("\\", "/").strip()
    if not source_norm:
        source_norm = f"data/derived/{symbol_norm}/{tf_norm}/klines.jsonl"

    status_norm = _normalize_simple_status(status)
    if status_norm not in {"OK", "WARN", "FAIL", "UNKNOWN"}:
        status_norm = "UNKNOWN"

    age_norm = None
    if age_h is not None:
        try:
            age_norm = round(float(age_h), 1)
        except Exception:
            age_norm = None

    reason_norm = "" if reason is None else str(reason).strip()

    return {
        "symbol": symbol_norm,
        "tf": tf_norm,
        "profile": profile_norm,
        "age_h": age_norm,
        "status": status_norm,
        "source": source_norm,
        "reason": reason_norm,
    }


def _build_freshness_table(now_utc: str, rows: list[dict]) -> dict:
    return {
        "generated_utc": now_utc,
        "ts_utc": now_utc,
        "default_profile": DEFAULT_FRESHNESS_PROFILE,
        "thresholds": {k: dict(v) for k, v in FRESHNESS_THRESHOLDS.items()},
        "rows": rows,
    }


def _normalize_coverage_status(status_raw):
    status = str(status_raw or "").upper().strip()
    if status in {"PASS", "OK", "DONE"}:
        return "PASS"
    if status in {"WARN", "IN_PROGRESS"}:
        return "WARN"
    if status in {"FAIL", "BLOCKED", "BLOCKED_DATA_QUALITY"}:
        return "FAIL"
    if status == "NEEDS_REBASE":
        return "NEEDS_REBASE"
    return "UNKNOWN"


def _collapse_system_status(statuses):
    normalized = [_normalize_simple_status(s) for s in statuses]
    if any(s == "FAIL" for s in normalized):
        return "FAIL"
    if any(s in {"WARN", "UNKNOWN"} for s in normalized):
        return "WARN"
    return "OK"


def _source_meta(path: Path, now_ts: float, ts_field_candidates=None):
    meta = {
        "path": str(path),
        "exists": path.exists(),
        "age_h": None,
        "ts_utc": None,
    }
    if not path.exists():
        return meta
    try:
        age_h = (now_ts - path.stat().st_mtime) / 3600.0
        meta["age_h"] = round(max(0.0, age_h), 2)
    except Exception:
        pass
    payload = read_json(path) or {}
    if isinstance(payload, dict):
        for key in (ts_field_candidates or ["ts_utc", "generated_utc", "timestamp"]):
            ts_val = payload.get(key)
            if isinstance(ts_val, str) and ts_val.strip():
                meta["ts_utc"] = ts_val
                break
    return meta


def _normalize_regime_snapshot(payload: dict, now_utc: str) -> dict:
    if not isinstance(payload, dict):
        return {}
    out = dict(payload)
    ts_utc = out.get("ts_utc") or out.get("timestamp_utc") or out.get("timestamp")
    if not isinstance(ts_utc, str) or not ts_utc.strip():
        ts_utc = now_utc
    out["ts_utc"] = ts_utc
    out.setdefault("updated_at_utc", ts_utc)
    return out


def _normalize_brake_snapshot(payload: dict, now_utc: str) -> dict:
    if not isinstance(payload, dict):
        return {}
    out = dict(payload)
    ts_utc = out.get("ts_utc") or out.get("updated_at_utc") or out.get("timestamp")
    if not isinstance(ts_utc, str) or not ts_utc.strip():
        ts_utc = now_utc
    out["ts_utc"] = ts_utc
    out.setdefault("updated_at_utc", ts_utc)
    if "status" not in out:
        status = "FAIL" if bool(out.get("overall_fail")) else "OK"
        results = out.get("results")
        if isinstance(results, list):
            for row in results:
                if not isinstance(row, dict):
                    continue
                row_status = _normalize_simple_status(row.get("status"))
                if row_status == "FAIL":
                    status = "FAIL"
                    break
                if row_status == "WARN" and status != "FAIL":
                    status = "WARN"
        out["status"] = status
    return out

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


def write_jsonl(path: Path, rows: list):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
    except Exception as e:
        logging.error(f"Failed to write snapshot {path}: {e}")


def _as_optional_number(value):
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _metric_status_from_row(row: dict) -> tuple[str, str | None]:
    missing = [k for k in ("score", "sharpe", "return", "mdd") if row.get(k) is None]
    if not missing:
        return "OK", None
    return "UNKNOWN", "missing_metrics:" + ",".join(missing)


def _score_sort_value(value) -> float:
    parsed = _as_optional_number(value)
    if parsed is None:
        return float("-inf")
    return parsed


def main():
    now_utc_obj = datetime.now(timezone.utc)
    now_utc = now_utc_obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    now_ts = time.time()

    # 1. Coverage input (atomic only; state_snapshots is canonical writer)
    cov_recs = read_jsonl(ATOMIC_COVERAGE_TABLE)
    write_jsonl(STATE_DIR / "coverage_table.jsonl", cov_recs)

    # 2. Coverage Latest
    latest_map = {}
    for r in cov_recs:
        key_obj = r.get("coverage_key", {})
        sym = key_obj.get("symbol", "UNKNOWN")
        tf = key_obj.get("timeframe", "UNKNOWN")
        regime = key_obj.get("regime", "UNKNOWN")
        mkey = f"{sym}_{tf}_{regime}"
        latest_map[mkey] = r

    write_json(STATE_DIR / "coverage_latest.json", latest_map)

    # 3. Coverage Summary
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

    # 4. Strategy Pool Summary
    pool_data = read_json(STATE_DIR / "strategy_pool.json") or {}
    candidates = pool_data.get("candidates", [])
    promoted = pool_data.get("promoted", [])
    demoted = pool_data.get("demoted", [])

    leaderboard = []
    for c in candidates:
        oos = c.get("last_oos_metrics", {}) if isinstance(c.get("last_oos_metrics"), dict) else {}
        candidate_metrics_status = str(c.get("metrics_status", "")).upper()
        candidate_reason = c.get("metrics_unavailable_reason")
        row = {
            "id": c.get("strategy_id", "unknown"),
            "score": _as_optional_number(c.get("last_score")),
            "sharpe": _as_optional_number(oos.get("sharpe")),
            "return": _as_optional_number(oos.get("return")),
            "mdd": _as_optional_number(oos.get("mdd")),
        }
        if candidate_metrics_status == "UNKNOWN":
            row["score"] = None
            row["sharpe"] = None
            row["return"] = None
            row["mdd"] = None
            row["metrics_status"] = "UNKNOWN"
            row["metrics_unavailable_reason"] = candidate_reason or "unknown_metrics_source"
        else:
            row["metrics_status"], row["metrics_unavailable_reason"] = _metric_status_from_row(row)
        leaderboard.append(row)
    leaderboard = sorted(leaderboard, key=lambda x: _score_sort_value(x.get("score")), reverse=True)[:10]

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

    # 5. Canonicalize Regime Monitor (state_snapshots is the final writer to data/state)
    regime_data = _normalize_regime_snapshot(read_json(ATOMIC_REGIME_MONITOR), now_utc)
    if isinstance(regime_data, dict) and regime_data:
        write_json(STATE_DIR / "regime_monitor_latest.json", regime_data)
    else:
        regime_data = {
            "ts_utc": now_utc,
            "updated_at_utc": now_utc,
            "overall": "UNKNOWN",
            "reason": ["missing_regime_atomic"],
            "current": {},
        }
        write_json(STATE_DIR / "regime_monitor_latest.json", regime_data)

    # 6. Regime Monitor Summary
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
        write_json(
            STATE_DIR / "regime_monitor_summary.json",
            {"status": "UNKNOWN", "updated_utc": now_utc, "last_updated_utc": now_utc},
        )

    # 7. Data Freshness 3x3
    freshness_matrix = []
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframes = ["1m", "1h", "4h"]

    for sym in symbols:
        for tf in timeframes:
            # Consistent with tg_cp: read only from derived
            p = Path(".") / f"data/derived/{sym}/{tf}/klines.jsonl"
            
            age_h = None
            source_error = None
            source = str(p.relative_to(Path(".")))
            
            if p.exists():
                try:
                    age_h = (now_ts - p.stat().st_mtime) / 3600.0
                except Exception as e:
                    source_error = f"stat_error: {str(e)}"
            else:
                source_error = "missing_source"

            profile = _freshness_profile_from_source(source, DEFAULT_FRESHNESS_PROFILE)
            status, reason = _evaluate_freshness_status(age_h, profile, source_error)
            
            freshness_matrix.append(
                _canonicalize_freshness_row(
                    symbol=sym,
                    tf=tf,
                    profile=profile,
                    age_h=age_h,
                    status=status,
                    source=source,
                    reason=reason,
                )
            )

    freshness_table = _build_freshness_table(now_utc, freshness_matrix)

    write_json(STATE_DIR / "freshness_table.json", freshness_table)

    # 8. Execution Mode Snapshot
    execution_mode = {
        "mode": os.getenv("EXECUTION_MODE", "unknown"),
        "last_updated_utc": now_utc
    }
    write_json(STATE_DIR / "execution_mode.json", execution_mode)

    # 9. Services Heartbeat Snapshot
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

    # 10. Coverage Matrix Snapshot
    cov_rows = cov_recs
    matrix_rows = []
    totals = {"done": 0, "inProgress": 0, "blocked": 0, "rebase": 0}
    
    # Track latest per (symbol, tf)
    latest_per_key = {}
    for r in cov_rows:
        key_obj = r.get("coverage_key", {})
        sym = key_obj.get("symbol", "UNKNOWN")
        tf = key_obj.get("timeframe", "UNKNOWN")
        k = (sym, tf)
        latest_per_key[k] = r
        
        status = r.get("status", "").upper()
        if status == "DONE": totals["done"] += 1
        elif status == "IN_PROGRESS": totals["inProgress"] += 1
        elif status == "BLOCKED_DATA_QUALITY": totals["blocked"] += 1
        elif status == "NEEDS_REBASE": totals["rebase"] += 1

    for (sym, tf), r in latest_per_key.items():
        status_raw = r.get("status", "").upper()
        status_map = "FAIL"
        if status_raw == "DONE": status_map = "PASS"
        elif status_raw == "IN_PROGRESS": status_map = "WARN"
        elif status_raw == "NEEDS_REBASE": status_map = "NEEDS_REBASE"
        
        # Best effort for earliest/latest from results or fallback to record timestamps
        res = r.get("results", {})
        is_range = res.get("is", {})
        oos_range = res.get("oos", {})
        
        earliest = is_range.get("start") or r.get("created_utc") or "N/A"
        latest = oos_range.get("end") or is_range.get("end") or r.get("updated_utc") or "N/A"
        
        lag_h = 0.0
        if latest != "N/A":
            try:
                # If latest is "now" or "2025-..."
                if latest == "now":
                    lag_h = 0.0
                else:
                    # Handle both ISO and simple date formats
                    clean_latest = latest.replace("Z", "+00:00")
                    if "T" not in clean_latest and " " not in clean_latest:
                        # Simple date "2024-12-31" -> add time
                        clean_latest += "T00:00:00+00:00"
                    
                    # fromisoformat handles +00:00
                    latest_ts = datetime.fromisoformat(clean_latest).timestamp()
                    lag_h = round((now_ts - latest_ts) / 3600.0, 1)
            except Exception as e:
                # logging.debug(f"Lag calculation failed for {latest}: {e}")
                pass

        matrix_rows.append({
            "symbol": sym,
            "tf": tf,
            "earliest": earliest,
            "latest": latest,
            "lag_hours": lag_h,
            "status": status_map
        })

    matrix_snapshot = {
        "ts_utc": now_utc,
        "rows": sorted(matrix_rows, key=lambda x: (x["symbol"], x["tf"])),
        "totals": totals
    }
    write_json(STATE_DIR / "coverage_matrix_latest.json", matrix_snapshot)

    # 11. Canonicalize Brake Health (state_snapshots is the final writer to data/state)
    brake_data = _normalize_brake_snapshot(read_json(ATOMIC_BRAKE_HEALTH), now_utc)
    if isinstance(brake_data, dict) and brake_data:
        write_json(STATE_DIR / "brake_health_latest.json", brake_data)
    else:
        brake_data = {
            "timestamp": now_utc,
            "ts_utc": now_utc,
            "updated_at_utc": now_utc,
            "overall_fail": False,
            "results": [],
            "strict_mode": False,
            "status": "UNKNOWN",
        }
        write_json(STATE_DIR / "brake_health_latest.json", brake_data)

    # 12. Optional Health Pack Aggregator (SSOT summary only)
    fresh_rows = freshness_table.get("rows", [])
    freshness_statuses = []
    freshness_non_ok = 0
    freshness_max_age = None
    if isinstance(fresh_rows, list):
        for row in fresh_rows:
            if not isinstance(row, dict):
                continue
            st = _normalize_simple_status(row.get("status"))
            freshness_statuses.append(st)
            if st != "OK":
                freshness_non_ok += 1
            age_v = row.get("age_h")
            try:
                age_f = float(age_v)
                freshness_max_age = age_f if freshness_max_age is None else max(freshness_max_age, age_f)
            except Exception:
                pass
    if not freshness_statuses:
        freshness_status = "UNKNOWN"
    elif "FAIL" in freshness_statuses:
        freshness_status = "FAIL"
    elif "WARN" in freshness_statuses:
        freshness_status = "WARN"
    elif "OK" in freshness_statuses:
        freshness_status = "OK"
    else:
        freshness_status = "UNKNOWN"

    cov_rows_status = []
    if isinstance(matrix_snapshot.get("rows"), list):
        for row in matrix_snapshot["rows"]:
            if not isinstance(row, dict):
                continue
            cov_rows_status.append(_normalize_coverage_status(row.get("status")))
    cov_totals = matrix_snapshot.get("totals", {}) if isinstance(matrix_snapshot, dict) else {}
    cov_done = int(cov_totals.get("done", 0) or 0)
    cov_in_progress = int(cov_totals.get("inProgress", 0) or 0)
    cov_blocked = int(cov_totals.get("blocked", 0) or 0)
    cov_rebase = int(cov_totals.get("rebase", 0) or 0)
    cov_total = cov_done + cov_in_progress + cov_blocked
    if cov_total <= 0 and not cov_rows_status and cov_rebase <= 0:
        coverage_status = "UNKNOWN"
    elif cov_blocked > 0 or "FAIL" in cov_rows_status:
        coverage_status = "FAIL"
    elif cov_rebase > 0 or "NEEDS_REBASE" in cov_rows_status or "WARN" in cov_rows_status:
        coverage_status = "WARN"
    elif cov_done > 0 or "PASS" in cov_rows_status:
        coverage_status = "PASS"
    else:
        coverage_status = "UNKNOWN"

    coverage_max_lag = None
    if isinstance(matrix_snapshot.get("rows"), list):
        for row in matrix_snapshot["rows"]:
            if not isinstance(row, dict):
                continue
            lag = row.get("lag_hours")
            try:
                lag_f = float(lag)
                coverage_max_lag = lag_f if coverage_max_lag is None else max(coverage_max_lag, lag_f)
            except Exception:
                pass

    brake_results = brake_data.get("results", []) if isinstance(brake_data, dict) else []
    if not isinstance(brake_results, list):
        brake_results = []
    brake_status = "UNKNOWN"
    if brake_results or bool(brake_data.get("overall_fail")):
        brake_status = "FAIL" if bool(brake_data.get("overall_fail")) else "OK"
        for row in brake_results:
            if not isinstance(row, dict):
                continue
            st = _normalize_simple_status(row.get("status"))
            if st == "FAIL":
                brake_status = "FAIL"
                break
            if st == "WARN" and brake_status != "FAIL":
                brake_status = "WARN"

    regime_path = STATE_DIR / "regime_monitor_latest.json"
    regime_data = read_json(regime_path) or {}
    regime_signal = _normalize_simple_status(regime_data.get("overall"))
    if regime_signal == "PASS":
        regime_signal = "OK"
    if regime_signal not in {"OK", "WARN", "FAIL"}:
        regime_signal = "UNKNOWN"
    regime_reasons = regime_data.get("reason")
    regime_top_reason = None
    if isinstance(regime_reasons, list) and regime_reasons:
        top_reason = regime_reasons[0]
        if isinstance(top_reason, str) and top_reason.strip():
            regime_top_reason = top_reason.strip()
    if regime_top_reason and len(regime_top_reason) > 120:
        regime_top_reason = regime_top_reason[:117] + "..."

    regime_age_h = None
    if regime_path.exists():
        try:
            regime_age_h = max(0.0, (now_ts - regime_path.stat().st_mtime) / 3600.0)
        except Exception:
            regime_age_h = None
    regime_monitor_status = "UNKNOWN"
    regime_ok_h = 12.0
    if regime_age_h is not None:
        regime_monitor_status = "OK" if regime_age_h <= regime_ok_h else "WARN"

    coverage_as_health = "OK" if coverage_status == "PASS" else coverage_status
    ssot_status = _collapse_system_status(
        [freshness_status, coverage_as_health, brake_status, regime_monitor_status]
    )

    system_health = {
        "generated_utc": now_utc,
        "ssot_semantics": "SystemHealth only (RegimeSignal is separate trade-risk alert)",
        "ssot_status": ssot_status,
        "refresh_hint": "bash scripts/refresh_state.sh",
        "components": {
            "freshness": {
                "status": freshness_status,
                "max_age_h": round(freshness_max_age, 1) if freshness_max_age is not None else None,
                "non_ok_rows": freshness_non_ok,
                "rows_total": len(fresh_rows) if isinstance(fresh_rows, list) else 0,
            },
            "coverage_matrix": {
                "status": coverage_status,
                "done": cov_done,
                "total": cov_total,
                "blocked": cov_blocked,
                "rebase": cov_rebase,
                "max_lag_h": round(coverage_max_lag, 1) if coverage_max_lag is not None else None,
            },
            "brake": {
                "status": brake_status,
            },
            "regime_monitor": {
                "status": regime_monitor_status,
                "age_h": round(regime_age_h, 1) if regime_age_h is not None else None,
                "ok_within_h": regime_ok_h,
            },
            "regime_signal": {
                "status": regime_signal,
                "top_reason": regime_top_reason,
            },
        },
        "sources": {
            "freshness_table.json": _source_meta(STATE_DIR / "freshness_table.json", now_ts),
            "coverage_matrix_latest.json": _source_meta(STATE_DIR / "coverage_matrix_latest.json", now_ts),
            "brake_health_latest.json": _source_meta(STATE_DIR / "brake_health_latest.json", now_ts, ["timestamp"]),
            "regime_monitor_latest.json": _source_meta(STATE_DIR / "regime_monitor_latest.json", now_ts),
        },
    }
    write_json(STATE_DIR / "system_health_latest.json", system_health)

    logging.info("Snapshots successfully written to data/state/")

if __name__ == "__main__":
    main()
    exit(0)
