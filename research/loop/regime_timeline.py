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

    history = [iv for iv in intervals if iv["start_dt"] <= as_of]
    chosen = history[-1] if history else intervals[0]
    return (chosen["start_utc"], chosen["end_utc"])


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
        return {
            "requested": "ALL",
            "applied": "ALL",
            "window_start_utc": None,
            "window_end_utc": None,
            "window_end_exclusive": True,
            "status": "OK",
            "rationale": "default_all_no_slice",
            "policy_path": policy.get("policy_path"),
            "warnings": policy.get("warnings", []),
            "as_of_utc": _iso_utc(as_of),
        }

    window = resolve_regime_window(requested, as_of, policy_payload=policy)
    if window is None:
        return {
            "requested": requested,
            "applied": "ALL",
            "window_start_utc": None,
            "window_end_utc": None,
            "window_end_exclusive": True,
            "status": "WARN",
            "rationale": "slice_unavailable_fallback_all",
            "policy_path": policy.get("policy_path"),
            "warnings": policy.get("warnings", []),
            "as_of_utc": _iso_utc(as_of),
        }

    return {
        "requested": requested,
        "applied": requested,
        "window_start_utc": window[0],
        "window_end_utc": window[1],
        "window_end_exclusive": True,
        "status": policy.get("status", "WARN"),
        "rationale": "slice_applied",
        "policy_path": policy.get("policy_path"),
        "warnings": policy.get("warnings", []),
        "as_of_utc": _iso_utc(as_of),
    }


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
