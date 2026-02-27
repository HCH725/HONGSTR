from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGIME_TIMELINE_PATH = REPO_ROOT / "research/policy/regime_timeline.json"

VALID_REGIMES = ("ALL", "BULL", "BEAR", "SIDEWAYS")
REGIME_ALIASES = {
    "ALL": "ALL",
    "BULL": "BULL",
    "LONG": "BULL",
    "BEAR": "BEAR",
    "SHORT": "BEAR",
    "SIDEWAYS": "SIDEWAYS",
    "NEUTRAL": "SIDEWAYS",
    "RANGE": "SIDEWAYS",
}


def normalize_regime_name(value: Any) -> str:
    text = str(value or "ALL").strip().upper()
    if not text:
        return "ALL"
    return REGIME_ALIASES.get(text, "ALL")


def load_regime_timeline_policy(policy_path: Path | None = None) -> dict[str, Any]:
    path = Path(policy_path or REGIME_TIMELINE_PATH)
    warnings: list[str] = []
    payload: dict[str, Any] = {
        "status": "WARN",
        "policy_path": _safe_rel(path),
        "warnings": warnings,
        "regimes": {"BULL": [], "BEAR": [], "SIDEWAYS": []},
    }

    if not path.exists():
        warnings.append("policy_missing")
        return payload

    try:
        raw_obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        warnings.append("policy_unreadable")
        return payload

    if not isinstance(raw_obj, dict):
        warnings.append("policy_not_object")
        return payload

    regimes_raw: dict[str, Any]
    if isinstance(raw_obj.get("regimes"), dict):
        regimes_raw = raw_obj.get("regimes") or {}
    else:
        regimes_raw = raw_obj

    for regime in ("BULL", "BEAR", "SIDEWAYS"):
        key = regime.lower()
        items = regimes_raw.get(key, [])
        if not isinstance(items, list):
            warnings.append(f"{key}_not_list")
            items = []

        parsed: list[dict[str, Any]] = []
        for idx, item in enumerate(items):
            iv = _parse_interval(item, regime=regime, index=idx, warnings=warnings)
            if iv is not None:
                parsed.append(iv)
        parsed.sort(key=lambda x: x["start_dt"])
        payload["regimes"][regime] = _dedupe_overlaps(parsed, regime=regime, warnings=warnings)

    _check_cross_regime_overlap(payload["regimes"], warnings)
    payload["status"] = "OK" if not warnings else "WARN"
    return payload


def resolve_regime_window(
    regime: Any,
    as_of_utc: Any = None,
    *,
    policy_path: Path | None = None,
    policy_payload: dict[str, Any] | None = None,
) -> tuple[str, str] | None:
    normalized = normalize_regime_name(regime)
    if normalized == "ALL":
        return None

    policy = policy_payload or load_regime_timeline_policy(policy_path)
    regimes = policy.get("regimes") if isinstance(policy, dict) else {}
    if not isinstance(regimes, dict):
        return None

    intervals = regimes.get(normalized) or []
    if not isinstance(intervals, list) or not intervals:
        return None

    as_of = _coerce_as_of_utc(as_of_utc)
    for iv in intervals:
        if iv["start_dt"] <= as_of < iv["end_dt"]:
            return (iv["start_utc"], iv["end_utc"])
    return None


def resolve_regime_context(
    regime: Any,
    *,
    as_of_utc: Any = None,
    policy_path: Path | None = None,
) -> dict[str, Any]:
    requested = normalize_regime_name(regime)
    as_of = _coerce_as_of_utc(as_of_utc)
    policy = load_regime_timeline_policy(policy_path)

    if requested == "ALL":
        rationale = "default_all_no_slice"
        return {
            "requested": "ALL",
            "applied": "ALL",
            "window_start_utc": None,
            "window_end_utc": None,
            "window_end_exclusive": True,
            "status": "OK",
            "rationale": rationale,
            "rationale_zh": _rationale_zh(rationale),
            "policy_path": policy.get("policy_path"),
            "warnings": policy.get("warnings", []),
            "as_of_utc": _iso_utc(as_of),
        }

    fallback = _resolve_policy_fallback_reason(policy, requested)
    if fallback:
        return {
            "requested": requested,
            "applied": "ALL",
            "window_start_utc": None,
            "window_end_utc": None,
            "window_end_exclusive": True,
            "status": "WARN",
            "rationale": fallback,
            "rationale_zh": _rationale_zh(fallback),
            "policy_path": policy.get("policy_path"),
            "warnings": policy.get("warnings", []),
            "as_of_utc": _iso_utc(as_of),
        }

    window = resolve_regime_window(requested, as_of, policy_payload=policy)
    if window is None:
        rationale = "window_not_found_fallback_all"
        return {
            "requested": requested,
            "applied": "ALL",
            "window_start_utc": None,
            "window_end_utc": None,
            "window_end_exclusive": True,
            "status": "WARN",
            "rationale": rationale,
            "rationale_zh": _rationale_zh(rationale),
            "policy_path": policy.get("policy_path"),
            "warnings": policy.get("warnings", []),
            "as_of_utc": _iso_utc(as_of),
        }

    rationale = "slice_applied"
    return {
        "requested": requested,
        "applied": requested,
        "window_start_utc": window[0],
        "window_end_utc": window[1],
        "window_end_exclusive": True,
        "status": "OK",
        "rationale": rationale,
        "rationale_zh": _rationale_zh(rationale),
        "policy_path": policy.get("policy_path"),
        "warnings": policy.get("warnings", []),
        "as_of_utc": _iso_utc(as_of),
    }


def _resolve_policy_fallback_reason(policy: dict[str, Any], requested: str) -> str | None:
    warnings = policy.get("warnings") if isinstance(policy, dict) else []
    if not isinstance(warnings, list):
        warnings = []

    if any(str(w) == "policy_missing" for w in warnings):
        return "policy_missing_fallback_all"

    invalid_markers = (
        "policy_unreadable",
        "policy_not_object",
        "_not_list",
        "_not_object",
        "_invalid_timestamp",
        "_invalid_range",
        "_overlap",
        "cross_regime_overlap",
    )
    if any(any(marker in str(w) for marker in invalid_markers) for w in warnings):
        return "policy_invalid_fallback_all"

    regimes = policy.get("regimes") if isinstance(policy, dict) else {}
    if not isinstance(regimes, dict):
        return "policy_invalid_fallback_all"
    intervals = regimes.get(requested)
    if not isinstance(intervals, list):
        return "policy_invalid_fallback_all"
    if not intervals:
        return "window_not_found_fallback_all"

    return None


def _rationale_zh(code: str) -> str:
    mapping = {
        "default_all_no_slice": "未指定切片，維持 ALL（全時段）預設模式。",
        "slice_applied": "已套用指定市場切片，僅使用該區間做回測。",
        "policy_missing_fallback_all": "找不到 regime policy，已自動降級為 ALL。",
        "policy_invalid_fallback_all": "regime policy 格式或區間不合法，已自動降級為 ALL。",
        "window_not_found_fallback_all": "指定切片在 as_of 時點無可用窗口，已自動降級為 ALL。",
    }
    return mapping.get(str(code), "切片資訊不足，已使用 ALL。")


def _parse_interval(
    item: Any,
    *,
    regime: str,
    index: int,
    warnings: list[str],
) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        warnings.append(f"{regime.lower()}[{index}]_not_object")
        return None

    start_raw = item.get("start") or item.get("start_utc")
    end_raw = item.get("end") or item.get("end_utc")
    start_dt = _parse_iso_utc(start_raw)
    end_dt = _parse_iso_utc(end_raw)
    if start_dt is None or end_dt is None:
        warnings.append(f"{regime.lower()}[{index}]_invalid_timestamp")
        return None
    if start_dt >= end_dt:
        warnings.append(f"{regime.lower()}[{index}]_invalid_range")
        return None

    return {
        "regime": regime,
        "label": str(item.get("label") or f"{regime.lower()}_{index}"),
        "start_utc": _iso_utc(start_dt),
        "end_utc": _iso_utc(end_dt),
        "start_dt": start_dt,
        "end_dt": end_dt,
    }


def _dedupe_overlaps(intervals: list[dict[str, Any]], *, regime: str, warnings: list[str]) -> list[dict[str, Any]]:
    if not intervals:
        return []
    out: list[dict[str, Any]] = [intervals[0]]
    for iv in intervals[1:]:
        prev = out[-1]
        if iv["start_dt"] < prev["end_dt"]:
            warnings.append(
                f"{regime.lower()}_overlap:{prev['start_utc']}..{prev['end_utc']} x {iv['start_utc']}..{iv['end_utc']}"
            )
            continue
        out.append(iv)
    return out


def _check_cross_regime_overlap(regimes: dict[str, Any], warnings: list[str]) -> None:
    rows: list[dict[str, Any]] = []
    for regime, intervals in regimes.items():
        if not isinstance(intervals, list):
            continue
        for iv in intervals:
            if isinstance(iv, dict):
                row = dict(iv)
                row["regime"] = regime
                rows.append(row)
    rows.sort(key=lambda x: x["start_dt"])

    for idx in range(1, len(rows)):
        prev = rows[idx - 1]
        cur = rows[idx]
        if cur["start_dt"] < prev["end_dt"] and cur["regime"] != prev["regime"]:
            warnings.append(
                "cross_regime_overlap:"
                f"{prev['regime']}[{prev['start_utc']}..{prev['end_utc']}] x "
                f"{cur['regime']}[{cur['start_utc']}..{cur['end_utc']}]"
            )


def _coerce_as_of_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    parsed = _parse_iso_utc(value)
    if parsed is not None:
        return parsed
    return datetime.now(timezone.utc)


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(normalized)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")
