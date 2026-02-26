from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "unreadable"
    if isinstance(data, dict):
        return data, None
    return None, "invalid"


def _score_from_status(status: str, mapping: dict[str, int]) -> int:
    return int(mapping.get(str(status or "").upper(), mapping.get("UNKNOWN", 0)))


def _fallback_brief(repo: Path, refresh_hint: str) -> dict[str, Any]:
    state = repo / "data/state"
    required = [
        state / "freshness_table.json",
        state / "coverage_matrix_latest.json",
        state / "brake_health_latest.json",
        state / "regime_monitor_latest.json",
    ]

    findings: list[str] = []
    evidence: list[str] = []

    loaded: dict[str, dict[str, Any]] = {}
    for p in required:
        data, err = _load_json(p)
        if data is None:
            findings.append(f"{p.name}: {err or 'missing'}")
            continue
        loaded[p.name] = data
        evidence.append(str(p.relative_to(repo)))

    if len(loaded) != len(required):
        return {
            "summary": {
                "status": "UNKNOWN",
                "generated_utc": None,
                "refresh_hint": refresh_hint,
                "report_only": True,
            },
            "score": {"health": 0, "data": 0, "latency": 0},
            "findings": findings or ["SSOT fallback inputs unavailable"],
            "evidence": evidence,
            "actions_suggested": [f"Run: {refresh_hint}"],
        }

    freshness = loaded["freshness_table.json"]
    coverage = loaded["coverage_matrix_latest.json"]
    brake = loaded["brake_health_latest.json"]
    regime = loaded["regime_monitor_latest.json"]

    fresh_rows = freshness.get("rows") or freshness.get("table") or []
    non_ok = [r for r in fresh_rows if str((r or {}).get("status", "UNKNOWN")).upper() != "OK"] if isinstance(fresh_rows, list) else []

    coverage_totals = coverage.get("totals") if isinstance(coverage, dict) else {}
    done = int((coverage_totals or {}).get("done", 0))
    total = int((coverage_totals or {}).get("total", done))
    max_lag_h = (coverage_totals or {}).get("max_lag_h")
    if max_lag_h is None:
        max_lag_h = 0

    brake_status = str(brake.get("status") or "UNKNOWN").upper()
    regime_status = str(regime.get("overall") or regime.get("status") or regime.get("overall_status") or "UNKNOWN").upper()

    health_status = "OK" if brake_status == "OK" and regime_status in {"OK", "PASS"} else "WARN"
    data_status = "OK" if not non_ok and (total == 0 or done >= total) else "WARN"

    latency_status = "OK"
    if isinstance(max_lag_h, (int, float)) and max_lag_h > 6:
        latency_status = "WARN"

    findings.extend(
        [
            f"fallback_mode: system_health_latest.json missing/unreadable; synthesized from SSOT components",
            f"freshness_non_ok_rows={len(non_ok)}",
            f"coverage_done_total={done}/{total}",
            f"brake_status={brake_status}",
            f"regime_monitor_status={regime_status}",
        ]
    )

    return {
        "summary": {
            "status": health_status,
            "generated_utc": freshness.get("ts_utc") or freshness.get("generated_utc") or coverage.get("ts_utc"),
            "refresh_hint": refresh_hint,
            "report_only": True,
        },
        "score": {
            "health": _score_from_status(health_status, {"OK": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
            "data": _score_from_status(data_status, {"OK": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
            "latency": _score_from_status(latency_status, {"OK": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
        },
        "findings": findings,
        "evidence": evidence,
        "actions_suggested": [] if health_status == "OK" else [f"Run: {refresh_hint}"],
    }


def build_system_health_morning_brief(repo: Path) -> dict[str, Any]:
    """Build read-only morning brief from SSOT snapshots only."""
    refresh_hint = "bash scripts/refresh_state.sh"
    health_path = repo / "data/state/system_health_latest.json"
    health_pack, err = _load_json(health_path)

    if health_pack is None:
        return _fallback_brief(repo, refresh_hint)

    ssot_status = str(health_pack.get("ssot_status") or "UNKNOWN").upper()
    components = health_pack.get("components") if isinstance(health_pack.get("components"), dict) else {}
    sources = health_pack.get("sources") if isinstance(health_pack.get("sources"), dict) else {}

    freshness_comp = components.get("freshness") if isinstance(components.get("freshness"), dict) else {}
    coverage_comp = components.get("coverage_matrix") if isinstance(components.get("coverage_matrix"), dict) else {}

    freshness_status = str(freshness_comp.get("status") or "UNKNOWN").upper()
    coverage_status = str(coverage_comp.get("status") or "UNKNOWN").upper()

    max_lag_h = coverage_comp.get("max_lag_h")
    if max_lag_h is None:
        max_lag_h = 0
    latency_status = "OK"
    if isinstance(max_lag_h, (int, float)) and max_lag_h > 6:
        latency_status = "WARN"

    evidence = []
    for key, meta in sources.items():
        if isinstance(meta, dict) and meta.get("path"):
            evidence.append(str(meta["path"]))
        elif isinstance(key, str) and key:
            evidence.append(f"data/state/{key}")

    findings = [
        f"ssot_status={ssot_status}",
        f"freshness_status={freshness_status}",
        f"coverage_status={coverage_status}",
    ]

    regime_signal = components.get("regime_signal") if isinstance(components.get("regime_signal"), dict) else {}
    signal_status = str(regime_signal.get("status") or "UNKNOWN").upper()
    top_reason = str(regime_signal.get("top_reason") or "").strip()
    if signal_status != "UNKNOWN":
        findings.append(f"regime_signal_status={signal_status}")
    if top_reason:
        findings.append(f"regime_signal_reason={top_reason}")

    return {
        "summary": {
            "status": ssot_status,
            "generated_utc": health_pack.get("ts_utc") or health_pack.get("generated_utc") or health_pack.get("updated_at_utc"),
            "refresh_hint": health_pack.get("refresh_hint") or refresh_hint,
            "report_only": True,
        },
        "score": {
            "health": _score_from_status(ssot_status, {"OK": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
            "data": _score_from_status(freshness_status if freshness_status != "UNKNOWN" else coverage_status, {"OK": 100, "PASS": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
            "latency": _score_from_status(latency_status, {"OK": 100, "WARN": 60, "FAIL": 20, "UNKNOWN": 0}),
        },
        "findings": findings,
        "evidence": evidence,
        "actions_suggested": [] if ssot_status == "OK" else [f"Run: {health_pack.get('refresh_hint') or refresh_hint}"],
    }
