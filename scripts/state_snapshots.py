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
from typing import Any, Optional

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
DAILY_REPORT_SCHEMA_VERSION = "daily_report.v1"
DAILY_REPORT_TOP_LEVEL_ORDER = [
    "schema",
    "generated_utc",
    "refresh_hint",
    "ssot_status",
    "ssot_components",
    "freshness_summary",
    "latest_backtest_head",
    "strategy_pool",
    "research_leaderboard",
    "governance",
    "guardrails",
    "sources",
]
DAILY_REPORT_FIELD_LABELS_ZH_EN = {
    "generated_utc": {"zh": "生成時間(UTC)", "en": "generated_utc"},
    "refresh_hint": {"zh": "更新提示", "en": "refresh_hint"},
    "ssot_status": {"zh": "系統總狀態", "en": "ssot_status"},
    "ssot_components": {"zh": "系統組件狀態", "en": "ssot_components"},
    "freshness_summary": {"zh": "資料新鮮度摘要", "en": "freshness_summary"},
    "latest_backtest_head": {"zh": "最新回測摘要", "en": "latest_backtest_head"},
    "strategy_pool": {"zh": "策略池摘要", "en": "strategy_pool"},
    "research_leaderboard": {"zh": "研究排行榜摘要", "en": "research_leaderboard"},
    "governance": {"zh": "治理摘要", "en": "governance"},
    "guardrails": {"zh": "護欄摘要", "en": "guardrails"},
    "sources": {"zh": "資料來源", "en": "sources"},
    "freshness_summary.profile_totals": {"zh": "新鮮度分檔統計", "en": "freshness_summary.profile_totals"},
    "latest_backtest_head.metrics": {"zh": "最新回測關鍵指標", "en": "latest_backtest_head.metrics"},
    "latest_backtest_head.regime_slice": {"zh": "最新回測切片", "en": "latest_backtest_head.regime_slice"},
    "latest_backtest_head.regime_window_start_utc": {"zh": "最新回測切片起點(UTC)", "en": "latest_backtest_head.regime_window_start_utc"},
    "latest_backtest_head.regime_window_end_utc": {"zh": "最新回測切片終點(UTC,不含)", "en": "latest_backtest_head.regime_window_end_utc"},
    "latest_backtest_head.regime_window_utc": {"zh": "最新回測切片區間(UTC)", "en": "latest_backtest_head.regime_window_utc"},
    "latest_backtest_head.slice_rationale": {"zh": "最新回測切片理由", "en": "latest_backtest_head.slice_rationale"},
    "latest_backtest_head.fallback_reason": {"zh": "最新回測降級原因", "en": "latest_backtest_head.fallback_reason"},
    "latest_backtest_head.slice_comparison_key": {"zh": "最新回測比較鍵", "en": "latest_backtest_head.slice_comparison_key"},
    "latest_backtest_head.regime_rationale_zh": {"zh": "最新回測切片原因(中文)", "en": "latest_backtest_head.regime_rationale_zh"},
    "strategy_pool.leaderboard_top": {"zh": "策略池排行前列", "en": "strategy_pool.leaderboard_top"},
    "strategy_pool.leaderboard_top.regime_slice": {"zh": "策略池排行切片", "en": "strategy_pool.leaderboard_top.regime_slice"},
    "strategy_pool.leaderboard_top.regime_window_start_utc": {"zh": "策略池排行切片起點(UTC)", "en": "strategy_pool.leaderboard_top.regime_window_start_utc"},
    "strategy_pool.leaderboard_top.regime_window_end_utc": {"zh": "策略池排行切片終點(UTC,不含)", "en": "strategy_pool.leaderboard_top.regime_window_end_utc"},
    "strategy_pool.leaderboard_top.regime_window_utc": {"zh": "策略池排行切片區間(UTC)", "en": "strategy_pool.leaderboard_top.regime_window_utc"},
    "strategy_pool.leaderboard_top.slice_rationale": {"zh": "策略池排行切片理由", "en": "strategy_pool.leaderboard_top.slice_rationale"},
    "strategy_pool.leaderboard_top.fallback_reason": {"zh": "策略池排行降級原因", "en": "strategy_pool.leaderboard_top.fallback_reason"},
    "strategy_pool.leaderboard_top.slice_comparison_key": {"zh": "策略池排行比較鍵", "en": "strategy_pool.leaderboard_top.slice_comparison_key"},
    "strategy_pool.direction_coverage": {"zh": "策略方向覆蓋摘要", "en": "strategy_pool.direction_coverage"},
    "strategy_pool.direction_coverage.short_coverage": {"zh": "空方覆蓋摘要", "en": "strategy_pool.direction_coverage.short_coverage"},
    "research_leaderboard.top_entries.regime_slice": {"zh": "研究排行切片", "en": "research_leaderboard.top_entries.regime_slice"},
    "research_leaderboard.top_entries.regime_window_start_utc": {"zh": "研究排行切片起點(UTC)", "en": "research_leaderboard.top_entries.regime_window_start_utc"},
    "research_leaderboard.top_entries.regime_window_end_utc": {"zh": "研究排行切片終點(UTC,不含)", "en": "research_leaderboard.top_entries.regime_window_end_utc"},
    "research_leaderboard.top_entries.regime_window_utc": {"zh": "研究排行切片區間(UTC)", "en": "research_leaderboard.top_entries.regime_window_utc"},
    "research_leaderboard.top_entries.slice_rationale": {"zh": "研究排行切片理由", "en": "research_leaderboard.top_entries.slice_rationale"},
    "research_leaderboard.top_entries.fallback_reason": {"zh": "研究排行降級原因", "en": "research_leaderboard.top_entries.fallback_reason"},
    "research_leaderboard.top_entries.slice_comparison_key": {"zh": "研究排行比較鍵", "en": "research_leaderboard.top_entries.slice_comparison_key"},
    "governance.today_gate_summary": {"zh": "今日Gate摘要", "en": "governance.today_gate_summary"},
    "ssot_components.regime_signal.threshold_value": {"zh": "RegimeSignal門檻值", "en": "ssot_components.regime_signal.threshold_value"},
    "ssot_components.regime_signal.threshold_source_path": {"zh": "RegimeSignal門檻來源路徑", "en": "ssot_components.regime_signal.threshold_source_path"},
    "ssot_components.regime_signal.threshold_policy_sha": {"zh": "RegimeSignal門檻版本SHA", "en": "ssot_components.regime_signal.threshold_policy_sha"},
    "ssot_components.regime_signal.threshold_rationale": {"zh": "RegimeSignal門檻理由", "en": "ssot_components.regime_signal.threshold_rationale"},
    "ssot_components.regime_signal.calibration_status": {"zh": "RegimeSignal校準狀態", "en": "ssot_components.regime_signal.calibration_status"},
    "ssot_components.regime_signal.last_calibrated_utc": {"zh": "RegimeSignal上次校準時間", "en": "ssot_components.regime_signal.last_calibrated_utc"},
}


def _daily_schema_spec() -> dict[str, Any]:
    return {
        "version": DAILY_REPORT_SCHEMA_VERSION,
        "top_level_order": list(DAILY_REPORT_TOP_LEVEL_ORDER),
        "field_labels_zh_en": dict(DAILY_REPORT_FIELD_LABELS_ZH_EN),
    }


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


def _as_float_opt(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _normalize_gate_status(status_raw: Any) -> str:
    status = str(status_raw or "UNKNOWN").upper().strip()
    if status in {"PASS", "OK", "DONE"}:
        return "PASS"
    if status in {"WARN", "IN_PROGRESS"}:
        return "WARN"
    if status in {"FAIL", "BLOCKED", "BLOCKED_DATA_QUALITY"}:
        return "FAIL"
    return "UNKNOWN"


def _metrics_status(required: dict[str, Any]) -> tuple[str, str | None]:
    missing = [k for k, v in required.items() if _as_float_opt(v) is None]
    if missing:
        return "UNKNOWN", "missing_metrics:" + ",".join(missing)
    return "OK", None


def _regime_rationale_zh(rationale: Any, explicit_zh: Any = None) -> str:
    explicit_text = str(explicit_zh or "").strip()
    if explicit_text:
        return explicit_text

    code = str(rationale or "").strip().lower()
    mapping = {
        "default_all_no_slice": "未指定切片，維持 ALL（全時段）預設模式。",
        "slice_applied": "已套用指定市場切片，僅使用該區間做回測。",
        "policy_missing_fallback_all": "找不到 regime policy，已自動降級為 ALL。",
        "policy_invalid_fallback_all": "regime policy 格式或區間不合法，已自動降級為 ALL。",
        "window_not_found_fallback_all": "指定切片在目前時點無可用窗口，已自動降級為 ALL。",
        "missing_research_leaderboard": "缺少研究排行榜資料，切片資訊不足，預設 ALL。",
    }
    return mapping.get(code, "")


def _regime_window_utc(start_utc: Any, end_utc: Any, explicit_window: Any = None) -> list[str] | None:
    if isinstance(explicit_window, (list, tuple)) and len(explicit_window) == 2:
        start = str(explicit_window[0] or "").strip()
        end = str(explicit_window[1] or "").strip()
        if start and end:
            return [start, end]

    # Backward compatibility with legacy string format: "[start,end)"
    explicit = str(explicit_window or "").strip()
    if explicit.startswith("[") and explicit.endswith(")") and "," in explicit:
        core = explicit[1:-1]
        raw_start, raw_end = core.split(",", 1)
        start = raw_start.strip()
        end = raw_end.strip()
        if start and end:
            return [start, end]

    start = str(start_utc or "").strip()
    end = str(end_utc or "").strip()
    if start and end:
        return [start, end]
    return None


def _slice_fallback_reason(
    *,
    regime_slice: Any,
    fallback_reason: Any,
    slice_rationale: Any,
) -> str | None:
    explicit = str(fallback_reason or "").strip()
    if explicit:
        zh = _regime_rationale_zh(explicit)
        return zh or explicit
    slice_norm = str(regime_slice or "ALL").upper().strip()
    if slice_norm != "ALL":
        return None
    rationale = str(slice_rationale or "").strip()
    if rationale and rationale != "default_all_no_slice":
        zh = _regime_rationale_zh(rationale)
        return zh or rationale
    return None


def _safe_rel_path(path_like: Any, root: Path) -> str:
    if not path_like:
        return ""
    p = Path(str(path_like))
    if not p.is_absolute():
        return str(p).replace("\\", "/")
    try:
        return str(p.resolve().relative_to(root.resolve())).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")


def _parse_ts_epoch(value: Any) -> float | None:
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw:
        return None
    try:
        normalized = raw
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def _freshness_summary(freshness_table: dict[str, Any]) -> dict[str, Any]:
    rows = freshness_table.get("rows", []) if isinstance(freshness_table, dict) else []
    counts = {"OK": 0, "WARN": 0, "FAIL": 0, "UNKNOWN": 0}
    profile_totals = {"realtime": 0, "backtest": 0}
    max_age_h = None
    offenders: list[dict[str, Any]] = []

    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        status = _normalize_simple_status(row.get("status"))
        if status not in counts:
            status = "UNKNOWN"
        counts[status] += 1

        profile = str(row.get("profile") or DEFAULT_FRESHNESS_PROFILE).lower().strip()
        if profile not in profile_totals:
            profile = DEFAULT_FRESHNESS_PROFILE
        profile_totals[profile] += 1

        age_h = _as_float_opt(row.get("age_h"))
        if age_h is not None:
            max_age_h = age_h if max_age_h is None else max(max_age_h, age_h)

        if status != "OK":
            offenders.append(
                {
                    "symbol": str(row.get("symbol") or "UNKNOWN"),
                    "tf": str(row.get("tf") or "UNKNOWN"),
                    "profile": profile,
                    "age_h": round(age_h, 1) if age_h is not None else None,
                    "status": status,
                    "reason": row.get("reason") or "",
                }
            )

    offenders_sorted = sorted(
        offenders,
        key=lambda x: float(x.get("age_h")) if _as_float_opt(x.get("age_h")) is not None else -1.0,
        reverse=True,
    )
    return {
        "counts": counts,
        "profile_totals": profile_totals,
        "total_rows": sum(counts.values()),
        "max_age_h": round(max_age_h, 1) if max_age_h is not None else None,
        "top_offenders": offenders_sorted[:5],
    }


def _strategy_pool_top_entries(pool_data: dict[str, Any], top_n: int = 5) -> list[dict[str, Any]]:
    rows = pool_data.get("candidates", []) if isinstance(pool_data, dict) else []
    out: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        metrics = row.get("last_oos_metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        score = _as_float_opt(row.get("last_score"))
        sharpe = _as_float_opt(metrics.get("sharpe"))
        ret = _as_float_opt(metrics.get("return"))
        mdd = _as_float_opt(metrics.get("mdd"))
        metrics_status, reason = _metrics_status(
            {"score": score, "oos_sharpe": sharpe, "oos_return": ret}
        )
        regime_slice = str(row.get("regime_slice") or row.get("regime") or "ALL").upper()
        start_utc = row.get("regime_window_start_utc")
        end_utc = row.get("regime_window_end_utc")
        regime_rationale = row.get("regime_rationale") or ""
        slice_rationale = row.get("slice_rationale") or regime_rationale or "default_all_no_slice"
        fallback_reason = _slice_fallback_reason(
            regime_slice=regime_slice,
            fallback_reason=row.get("fallback_reason"),
            slice_rationale=slice_rationale,
        )
        out.append(
            {
                "strategy_id": row.get("strategy_id") or "unknown",
                "candidate_id": row.get("candidate_id") or "",
                "family": row.get("family") or "unknown",
                "direction": row.get("direction") or "UNKNOWN",
                "variant": row.get("variant") or "base",
                "regime_slice": regime_slice,
                "regime_window_start_utc": start_utc,
                "regime_window_end_utc": end_utc,
                "regime_window_utc": _regime_window_utc(start_utc, end_utc, row.get("regime_window_utc")),
                "slice_rationale": slice_rationale,
                "fallback_reason": fallback_reason,
                "regime_rationale": regime_rationale,
                "regime_rationale_zh": _regime_rationale_zh(regime_rationale, row.get("regime_rationale_zh")),
                "slice_comparison_key": row.get("slice_comparison_key")
                or f"{row.get('strategy_id') or 'unknown'}|{str(row.get('direction') or 'UNKNOWN').upper()}|{row.get('variant') or 'base'}|{regime_slice}",
                "score": score,
                "oos_sharpe": sharpe,
                "oos_return": ret,
                "oos_mdd": mdd,
                "gate_overall": _normalize_gate_status(row.get("gate_overall")),
                "recommendation": str(row.get("recommendation") or "UNKNOWN").upper(),
                "metrics_status": metrics_status,
                "metrics_unavailable_reason": reason,
                "report_dir": row.get("report_dir") or "",
            }
        )
    ranked = sorted(
        out,
        key=lambda x: (
            float(x.get("score")) if _as_float_opt(x.get("score")) is not None else float("-inf"),
            float(x.get("oos_sharpe")) if _as_float_opt(x.get("oos_sharpe")) is not None else float("-inf"),
        ),
        reverse=True,
    )
    return ranked[:top_n]


def _strategy_pool_direction_coverage(pool_data: dict[str, Any]) -> dict[str, Any]:
    rows = pool_data.get("candidates", []) if isinstance(pool_data, dict) else []
    direction_counts = {"LONG": 0, "SHORT": 0, "LONGSHORT": 0, "UNKNOWN": 0}
    short_rows: list[dict[str, Any]] = []

    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        direction_raw = str(row.get("direction") or "UNKNOWN").upper().strip()
        direction = direction_raw if direction_raw in direction_counts else "UNKNOWN"
        direction_counts[direction] += 1

        if direction != "SHORT":
            continue

        metrics = row.get("last_oos_metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}
        score = _as_float_opt(row.get("last_score"))
        oos_sharpe = _as_float_opt(metrics.get("sharpe"))
        oos_return = _as_float_opt(metrics.get("return"))
        metrics_status, reason = _metrics_status(
            {"score": score, "oos_sharpe": oos_sharpe, "oos_return": oos_return}
        )
        regime_slice = str(row.get("regime_slice") or row.get("regime") or "ALL").upper()
        start_utc = row.get("regime_window_start_utc")
        end_utc = row.get("regime_window_end_utc")
        regime_rationale = row.get("regime_rationale") or ""
        slice_rationale = row.get("slice_rationale") or regime_rationale or "default_all_no_slice"
        fallback_reason = _slice_fallback_reason(
            regime_slice=regime_slice,
            fallback_reason=row.get("fallback_reason"),
            slice_rationale=slice_rationale,
        )
        short_rows.append(
            {
                "strategy_id": row.get("strategy_id") or "unknown",
                "candidate_id": row.get("candidate_id") or "",
                "direction": "SHORT",
                "regime_slice": regime_slice,
                "regime_window_start_utc": start_utc,
                "regime_window_end_utc": end_utc,
                "regime_window_utc": _regime_window_utc(start_utc, end_utc, row.get("regime_window_utc")),
                "slice_rationale": slice_rationale,
                "fallback_reason": fallback_reason,
                "regime_rationale": regime_rationale,
                "regime_rationale_zh": _regime_rationale_zh(regime_rationale, row.get("regime_rationale_zh")),
                "slice_comparison_key": row.get("slice_comparison_key")
                or f"{row.get('strategy_id') or 'unknown'}|SHORT|{row.get('variant') or 'base'}|{regime_slice}",
                "gate_overall": _normalize_gate_status(row.get("gate_overall")),
                "score": score,
                "oos_sharpe": oos_sharpe,
                "oos_return": oos_return,
                "metrics_status": metrics_status,
                "metrics_unavailable_reason": reason,
            }
        )

    short_pass = sum(1 for r in short_rows if r.get("gate_overall") == "PASS")
    short_ranked = sorted(
        short_rows,
        key=lambda x: (
            float(x.get("score")) if _as_float_opt(x.get("score")) is not None else float("-inf"),
            float(x.get("oos_sharpe")) if _as_float_opt(x.get("oos_sharpe")) is not None else float("-inf"),
        ),
        reverse=True,
    )
    best_entry = short_ranked[0] if short_ranked else None

    return {
        "counts": {
            "long": direction_counts["LONG"],
            "short": direction_counts["SHORT"],
            "longshort": direction_counts["LONGSHORT"],
            "unknown": direction_counts["UNKNOWN"],
        },
        "short_coverage": {
            "candidates": len(short_rows),
            "gate_pass": short_pass,
            "best_entry": best_entry,
            "best_entry_reason": None if best_entry else "no_short_candidates",
        },
    }


def _research_top_entries(leaderboard: dict[str, Any], top_n: int = 5) -> list[dict[str, Any]]:
    rows = leaderboard.get("entries", []) if isinstance(leaderboard, dict) else []
    out: list[dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        score = _as_float_opt(row.get("final_score"))
        sharpe = _as_float_opt(row.get("oos_sharpe"))
        mdd = _as_float_opt(row.get("oos_mdd"))
        is_sharpe = _as_float_opt(row.get("is_sharpe"))
        metrics_status, reason = _metrics_status(
            {"final_score": score, "oos_sharpe": sharpe, "oos_mdd": mdd}
        )
        regime_slice = str(row.get("regime_slice") or row.get("regime") or "ALL").upper()
        start_utc = row.get("regime_window_start_utc")
        end_utc = row.get("regime_window_end_utc")
        regime_rationale = row.get("regime_rationale") or ""
        slice_rationale = row.get("slice_rationale") or regime_rationale or "default_all_no_slice"
        fallback_reason = _slice_fallback_reason(
            regime_slice=regime_slice,
            fallback_reason=row.get("fallback_reason"),
            slice_rationale=slice_rationale,
        )
        out.append(
            {
                "candidate_id": row.get("candidate_id") or row.get("experiment_id") or "unknown",
                "strategy_id": row.get("strategy_id") or "unknown",
                "family": row.get("family") or "unknown",
                "direction": row.get("direction") or "UNKNOWN",
                "variant": row.get("variant") or "base",
                "regime_slice": regime_slice,
                "regime_window_start_utc": start_utc,
                "regime_window_end_utc": end_utc,
                "regime_window_utc": _regime_window_utc(start_utc, end_utc, row.get("regime_window_utc")),
                "slice_rationale": slice_rationale,
                "fallback_reason": fallback_reason,
                "regime_rationale": regime_rationale,
                "regime_rationale_zh": _regime_rationale_zh(regime_rationale, row.get("regime_rationale_zh")),
                "slice_comparison_key": row.get("slice_comparison_key")
                or f"{row.get('strategy_id') or 'unknown'}|{str(row.get('direction') or 'UNKNOWN').upper()}|{row.get('variant') or 'base'}|{regime_slice}",
                "status": str(row.get("status") or "UNKNOWN").upper(),
                "gate_overall": _normalize_gate_status(row.get("gate_overall")),
                "final_score": score,
                "oos_sharpe": sharpe,
                "oos_mdd": mdd,
                "is_sharpe": is_sharpe,
                "trades_count": int(float(row.get("trades_count"))) if _as_float_opt(row.get("trades_count")) is not None else None,
                "metrics_status": str(row.get("metrics_status") or metrics_status).upper(),
                "metrics_unavailable_reason": row.get("metrics_unavailable_reason") or reason,
                "timestamp": row.get("timestamp") or "",
                "report_dir": row.get("report_dir") or "",
            }
        )
    ranked = sorted(
        out,
        key=lambda x: (
            float(x.get("final_score")) if _as_float_opt(x.get("final_score")) is not None else float("-inf"),
            float(x.get("oos_sharpe")) if _as_float_opt(x.get("oos_sharpe")) is not None else float("-inf"),
        ),
        reverse=True,
    )
    return ranked[:top_n]


def _latest_backtest_head(leaderboard: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    rows = leaderboard.get("entries", []) if isinstance(leaderboard, dict) else []
    if not isinstance(rows, list) or not rows:
        return {
            "status": "UNKNOWN",
            "reason": "missing_research_leaderboard",
            "artifacts": {"report_dir": "", "summary": "", "gate": "", "selection": ""},
            "metrics": {
                "final_score": None,
                "oos_sharpe": None,
                "oos_mdd": None,
                "is_sharpe": None,
                "trades_count": None,
            },
            "regime_slice": "ALL",
            "regime_window_start_utc": None,
            "regime_window_end_utc": None,
            "regime_window_utc": None,
            "regime_window_end_exclusive": True,
            "slice_rationale": "missing_research_leaderboard",
            "fallback_reason": "missing_research_leaderboard",
            "regime_rationale": "missing_research_leaderboard",
            "regime_rationale_zh": _regime_rationale_zh("missing_research_leaderboard"),
            "slice_comparison_key": "unknown|UNKNOWN|base|ALL",
            "gate": {"overall": "UNKNOWN", "recommendation": "UNKNOWN"},
            "metrics_status": "UNKNOWN",
            "metrics_unavailable_reason": "missing_metrics:final_score,oos_sharpe,oos_mdd",
        }

    chosen = max(
        (r for r in rows if isinstance(r, dict)),
        key=lambda x: _parse_ts_epoch(x.get("timestamp")) or 0.0,
    )
    report_dir_raw = chosen.get("report_dir") or ""
    report_dir_path = Path(str(report_dir_raw)) if report_dir_raw else None
    if report_dir_path and not report_dir_path.is_absolute():
        report_dir_path = repo_root / report_dir_path

    summary_path = report_dir_path / "summary.json" if report_dir_path else None
    gate_path = report_dir_path / "gate.json" if report_dir_path else None
    selection_path = report_dir_path / "selection.json" if report_dir_path else None
    summary_obj = read_json(summary_path) if summary_path and summary_path.exists() else {}
    gate_obj = read_json(gate_path) if gate_path and gate_path.exists() else {}
    if not isinstance(summary_obj, dict):
        summary_obj = {}
    if not isinstance(gate_obj, dict):
        gate_obj = {}

    final_score = _as_float_opt(chosen.get("final_score"))
    if final_score is None:
        final_score = _as_float_opt(gate_obj.get("final_score"))
    oos_sharpe = _as_float_opt(chosen.get("oos_sharpe"))
    if oos_sharpe is None:
        oos_sharpe = _as_float_opt(summary_obj.get("sharpe"))
    oos_mdd = _as_float_opt(chosen.get("oos_mdd"))
    if oos_mdd is None:
        oos_mdd = _as_float_opt(summary_obj.get("max_drawdown"))
    is_sharpe = _as_float_opt(chosen.get("is_sharpe"))
    if is_sharpe is None:
        is_sharpe = _as_float_opt(summary_obj.get("is_sharpe"))
    trades_count = _as_float_opt(chosen.get("trades_count"))
    if trades_count is None:
        trades_count = _as_float_opt(summary_obj.get("trades_count"))

    metrics_status, reason = _metrics_status(
        {"final_score": final_score, "oos_sharpe": oos_sharpe, "oos_mdd": oos_mdd}
    )
    gate_overall = _normalize_gate_status(chosen.get("gate_overall") or gate_obj.get("overall"))
    recommendation = str(gate_obj.get("recommendation") or "UNKNOWN").upper()
    if recommendation not in {"PROMOTE", "WATCHLIST", "DEMOTE", "UNKNOWN"}:
        recommendation = "UNKNOWN"
    regime_slice = str(
        chosen.get("regime_slice")
        or chosen.get("regime")
        or summary_obj.get("regime_slice")
        or summary_obj.get("regime")
        or "ALL"
    ).upper()
    start_utc = chosen.get("regime_window_start_utc") or summary_obj.get("regime_window_start_utc")
    end_utc = chosen.get("regime_window_end_utc") or summary_obj.get("regime_window_end_utc")
    regime_rationale = chosen.get("regime_rationale") or summary_obj.get("regime_rationale") or ""
    slice_rationale = chosen.get("slice_rationale") or summary_obj.get("slice_rationale") or regime_rationale or "default_all_no_slice"
    fallback_reason = _slice_fallback_reason(
        regime_slice=regime_slice,
        fallback_reason=chosen.get("fallback_reason") or summary_obj.get("fallback_reason"),
        slice_rationale=slice_rationale,
    )
    comparison_key = chosen.get("slice_comparison_key") or summary_obj.get("slice_comparison_key")
    if not comparison_key:
        comparison_key = (
            f"{chosen.get('strategy_id') or summary_obj.get('strategy_id') or 'unknown'}|"
            f"{str(chosen.get('direction') or summary_obj.get('direction') or 'UNKNOWN').upper()}|"
            f"{chosen.get('variant') or summary_obj.get('variant') or 'base'}|{regime_slice}"
        )

    return {
        "status": "OK",
        "candidate_id": chosen.get("candidate_id") or chosen.get("experiment_id") or "unknown",
        "strategy_id": chosen.get("strategy_id") or "unknown",
        "direction": chosen.get("direction") or summary_obj.get("direction") or "UNKNOWN",
        "variant": chosen.get("variant") or summary_obj.get("variant") or "base",
        "regime_slice": regime_slice,
        "regime_window_start_utc": start_utc,
        "regime_window_end_utc": end_utc,
        "regime_window_utc": _regime_window_utc(start_utc, end_utc, chosen.get("regime_window_utc") or summary_obj.get("regime_window_utc")),
        "regime_window_end_exclusive": bool(chosen.get("regime_window_end_exclusive", summary_obj.get("regime_window_end_exclusive", True))),
        "slice_rationale": slice_rationale,
        "fallback_reason": fallback_reason,
        "regime_rationale": regime_rationale,
        "regime_rationale_zh": _regime_rationale_zh(
            regime_rationale,
            chosen.get("regime_rationale_zh") or summary_obj.get("regime_rationale_zh"),
        ),
        "slice_comparison_key": comparison_key,
        "timestamp": chosen.get("timestamp") or "",
        "artifacts": {
            "report_dir": _safe_rel_path(report_dir_path or "", repo_root),
            "summary": _safe_rel_path(summary_path or "", repo_root),
            "gate": _safe_rel_path(gate_path or "", repo_root),
            "selection": _safe_rel_path(selection_path or "", repo_root),
        },
        "metrics": {
            "final_score": final_score,
            "oos_sharpe": oos_sharpe,
            "oos_mdd": oos_mdd,
            "is_sharpe": is_sharpe,
            "trades_count": int(trades_count) if trades_count is not None else None,
        },
        "gate": {"overall": gate_overall, "recommendation": recommendation},
        "metrics_status": metrics_status,
        "metrics_unavailable_reason": reason,
    }


def _governance_summary(leaderboard: dict[str, Any], policy_payload: dict[str, Any], now_utc: str) -> dict[str, Any]:
    rows = leaderboard.get("entries", []) if isinstance(leaderboard, dict) else []
    today = now_utc[:10]
    today_rows = [
        r for r in rows if isinstance(r, dict) and str(r.get("timestamp") or "").startswith(today)
    ]
    scope = "today_utc" if today_rows else "all_entries_fallback"
    target_rows = today_rows if today_rows else [r for r in rows if isinstance(r, dict)]
    counts = {"PASS": 0, "WARN": 0, "FAIL": 0, "UNKNOWN": 0}
    for row in target_rows:
        gate_st = _normalize_gate_status(row.get("gate_overall"))
        counts[gate_st] = counts.get(gate_st, 0) + 1

    return {
        "overfit_gates_policy": {
            "name": str(policy_payload.get("name") or "UNKNOWN"),
            "path": "research/policy/overfit_gates_aggressive.json",
        },
        "today_gate_summary": {
            "date_utc": today,
            "scope": scope,
            "total": sum(counts.values()),
            "pass": counts["PASS"],
            "warn": counts["WARN"],
            "fail": counts["FAIL"],
            "unknown": counts["UNKNOWN"],
        },
    }


def _guardrails_summary(pool_data: dict[str, Any], loop_state: dict[str, Any]) -> dict[str, Any]:
    report_only_val = pool_data.get("report_only") if isinstance(pool_data, dict) else None
    actions = loop_state.get("actions") if isinstance(loop_state, dict) else None
    actions_empty = isinstance(actions, list) and len(actions) == 0
    return {
        "status": "PASS" if report_only_val is True and actions_empty else "WARN",
        "checks": {
            "report_only_from_strategy_pool": {
                "status": "PASS" if report_only_val is True else "UNKNOWN",
                "value": report_only_val,
                "source": "data/state/strategy_pool.json#report_only",
            },
            "actions_empty_from_loop_state": {
                "status": "PASS" if actions_empty else "UNKNOWN",
                "value": actions if isinstance(actions, list) else None,
                "source": "data/state/_research/loop_state.json#actions",
            },
            "core_diff_src_hongstr": {"status": "PASS_EXPECTED", "source": "preflight_required"},
            "tg_cp_no_exec": {"status": "PASS_EXPECTED", "source": "preflight_required"},
            "no_data_committed": {"status": "PASS_EXPECTED", "source": "preflight_required"},
        },
    }


def _build_daily_report_payload(
    *,
    now_utc: str,
    now_ts: float,
    system_health: dict[str, Any],
    freshness_table: dict[str, Any],
    strategy_pool_summary: dict[str, Any],
    strategy_pool_data: dict[str, Any],
    research_leaderboard: dict[str, Any],
    loop_state: dict[str, Any],
    policy_payload: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    components = system_health.get("components", {}) if isinstance(system_health, dict) else {}
    if not isinstance(components, dict):
        components = {}
    pool_counts = strategy_pool_summary.get("counts", {}) if isinstance(strategy_pool_summary, dict) else {}
    if not isinstance(pool_counts, dict):
        pool_counts = {}

    payload = {
        "schema": _daily_schema_spec(),
        "generated_utc": now_utc,
        "refresh_hint": str(system_health.get("refresh_hint") or "bash scripts/refresh_state.sh"),
        "ssot_status": str(system_health.get("ssot_status") or "UNKNOWN"),
        "ssot_components": components,
        "freshness_summary": _freshness_summary(freshness_table),
        "latest_backtest_head": _latest_backtest_head(research_leaderboard, repo_root),
        "strategy_pool": {
            "summary": {
                "counts": {
                    "candidates": int(pool_counts.get("candidates", 0) or 0),
                    "promoted": int(pool_counts.get("promoted", 0) or 0),
                    "demoted": int(pool_counts.get("demoted", 0) or 0),
                },
                "last_updated_utc": strategy_pool_summary.get("last_updated_utc"),
            },
            "leaderboard_top": _strategy_pool_top_entries(strategy_pool_data, top_n=5),
            "direction_coverage": _strategy_pool_direction_coverage(strategy_pool_data),
        },
        "research_leaderboard": {
            "generated_at": research_leaderboard.get("generated_at") if isinstance(research_leaderboard, dict) else None,
            "top_n": int(research_leaderboard.get("top_n", 0) or 0) if isinstance(research_leaderboard, dict) else 0,
            "top_entries": _research_top_entries(research_leaderboard, top_n=5),
        },
        "governance": _governance_summary(research_leaderboard, policy_payload, now_utc),
        "guardrails": _guardrails_summary(strategy_pool_data, loop_state),
        "sources": {
            "system_health_latest": _source_meta(STATE_DIR / "system_health_latest.json", now_ts),
            "freshness_table": _source_meta(STATE_DIR / "freshness_table.json", now_ts),
            "strategy_pool_summary": _source_meta(STATE_DIR / "strategy_pool_summary.json", now_ts),
            "strategy_pool": _source_meta(STATE_DIR / "strategy_pool.json", now_ts),
            "research_leaderboard": _source_meta(STATE_DIR / "_research/leaderboard.json", now_ts, ["generated_at"]),
            "research_loop_state": _source_meta(STATE_DIR / "_research/loop_state.json", now_ts, ["last_run"]),
        },
    }

    ordered_payload: dict[str, Any] = {}
    for key in DAILY_REPORT_TOP_LEVEL_ORDER:
        ordered_payload[key] = payload.get(key)
    return ordered_payload


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
    regime_threshold_value = _as_float_opt(regime_data.get("threshold_value"))
    regime_threshold_source_path_raw = str(regime_data.get("threshold_source_path") or "").strip()
    regime_threshold_source_path = regime_threshold_source_path_raw or None
    regime_threshold_policy_sha_raw = str(regime_data.get("threshold_policy_sha") or "").strip()
    regime_threshold_policy_sha = regime_threshold_policy_sha_raw or None
    regime_threshold_rationale_raw = str(regime_data.get("threshold_rationale") or "").strip()
    regime_threshold_rationale = regime_threshold_rationale_raw or None
    regime_calibration_status_raw = str(regime_data.get("calibration_status") or "").upper().strip()
    regime_calibration_status = regime_calibration_status_raw if regime_calibration_status_raw in {"OK", "WARN", "STALE", "UNKNOWN"} else "UNKNOWN"
    regime_last_calibrated_raw = regime_data.get("last_calibrated_utc")
    regime_last_calibrated_utc = str(regime_last_calibrated_raw).strip() if isinstance(regime_last_calibrated_raw, str) and str(regime_last_calibrated_raw).strip() else None

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
                "threshold_value": regime_threshold_value,
                "threshold_source_path": regime_threshold_source_path,
                "threshold_policy_sha": regime_threshold_policy_sha,
                "threshold_rationale": regime_threshold_rationale,
                "calibration_status": regime_calibration_status,
                "last_calibrated_utc": regime_last_calibrated_utc,
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

    # 13. Daily Report SSOT (single entrypoint for tg_cp/dashboard daily reporting)
    research_leaderboard = read_json(STATE_DIR / "_research/leaderboard.json") or {}
    loop_state = read_json(STATE_DIR / "_research/loop_state.json") or {}
    overfit_policy = read_json(Path("research/policy/overfit_gates_aggressive.json")) or {}
    daily_report_payload = _build_daily_report_payload(
        now_utc=now_utc,
        now_ts=now_ts,
        system_health=system_health if isinstance(system_health, dict) else {},
        freshness_table=freshness_table if isinstance(freshness_table, dict) else {},
        strategy_pool_summary=pool_summary if isinstance(pool_summary, dict) else {},
        strategy_pool_data=pool_data if isinstance(pool_data, dict) else {},
        research_leaderboard=research_leaderboard if isinstance(research_leaderboard, dict) else {},
        loop_state=loop_state if isinstance(loop_state, dict) else {},
        policy_payload=overfit_policy if isinstance(overfit_policy, dict) else {},
        repo_root=Path(".").resolve(),
    )
    write_json(STATE_DIR / "daily_report_latest.json", daily_report_payload)

    logging.info("Snapshots successfully written to data/state/")

if __name__ == "__main__":
    main()
    exit(0)
