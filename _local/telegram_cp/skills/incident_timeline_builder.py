from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REFRESH_HINT = "bash scripts/refresh_state.sh"


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "unreadable"
    if not isinstance(obj, dict):
        return None, "invalid"
    return obj, None


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


def _unknown_payload(start: str, end: str, env: str, findings: list[str], evidence: list[str]) -> dict[str, Any]:
    return {
        "summary": {
            "status": "UNKNOWN",
            "report_only": True,
            "env": env,
            "time_range": {"start": start, "end": end},
            "refresh_hint": REFRESH_HINT,
            "source_mode": "ssot_missing",
        },
        "timeline": [
            {
                "ts": None,
                "source": "ssot",
                "event": "SSOT inputs missing or unreadable",
                "evidence_ref": REFRESH_HINT,
            }
        ],
        "suspected_root_causes": findings or ["SSOT snapshots missing or unreadable"],
        "next_questions": [
            "Have you run bash scripts/refresh_state.sh?",
            "Are canonical state snapshots present under data/state/?",
        ],
    }


def _build_from_health_pack(repo: Path, pack: dict[str, Any], start: str, end: str, env: str) -> dict[str, Any]:
    status = str(pack.get("ssot_status") or "UNKNOWN").upper()
    generated = pack.get("ts_utc") or pack.get("generated_utc") or pack.get("updated_at_utc")
    components = pack.get("components") if isinstance(pack.get("components"), dict) else {}
    sources = pack.get("sources") if isinstance(pack.get("sources"), dict) else {}

    timeline: list[dict[str, Any]] = []
    timeline.append(
        {
            "ts": generated,
            "source": "data/state/system_health_latest.json",
            "event": f"System health status: {status}",
            "evidence_ref": "data/state/system_health_latest.json#ssot_status",
        }
    )

    suspected: list[str] = []
    regime_signal = components.get("regime_signal") if isinstance(components.get("regime_signal"), dict) else {}
    sig_status = str(regime_signal.get("status") or "UNKNOWN").upper()
    sig_reason = str(regime_signal.get("top_reason") or "").strip()
    if sig_status in {"WARN", "FAIL"}:
        suspected.append(f"RegimeSignal {sig_status}: {sig_reason or 'risk detected'}")

    freshness = components.get("freshness") if isinstance(components.get("freshness"), dict) else {}
    fresh_non_ok = int(freshness.get("non_ok_rows", 0) or 0)
    if fresh_non_ok > 0:
        suspected.append(f"Freshness non_ok_rows={fresh_non_ok}")

    coverage = components.get("coverage_matrix") if isinstance(components.get("coverage_matrix"), dict) else {}
    max_lag_h = coverage.get("max_lag_h")
    if isinstance(max_lag_h, (int, float)) and max_lag_h > 6:
        suspected.append(f"Coverage lag elevated: {max_lag_h}h")

    evidence: list[str] = []
    for name, meta in sources.items():
        if isinstance(meta, dict) and meta.get("path"):
            evidence.append(str(meta.get("path")))
            timeline.append(
                {
                    "ts": meta.get("ts_utc"),
                    "source": str(meta.get("path")),
                    "event": f"Source snapshot {name}: exists={meta.get('exists')}",
                    "evidence_ref": f"{meta.get('path')}#ts_utc",
                }
            )

    next_questions = [
        "Did status transitions align with the selected time range?",
        "Any upstream ETL/state refresh anomalies before this window?",
    ]
    if status in {"WARN", "FAIL", "UNKNOWN"}:
        next_questions.append(f"Run: {pack.get('refresh_hint') or REFRESH_HINT}")

    return {
        "summary": {
            "status": status,
            "report_only": True,
            "env": env,
            "time_range": {"start": start, "end": end},
            "refresh_hint": pack.get("refresh_hint") or REFRESH_HINT,
            "source_mode": "system_health_latest",
        },
        "timeline": timeline,
        "suspected_root_causes": suspected,
        "next_questions": next_questions,
    }


def _build_from_fallback(repo: Path, start: str, end: str, env: str) -> dict[str, Any]:
    state = repo / "data/state"
    required = [
        state / "freshness_table.json",
        state / "coverage_matrix_latest.json",
        state / "brake_health_latest.json",
        state / "regime_monitor_latest.json",
    ]
    loaded: dict[str, dict[str, Any]] = {}
    findings: list[str] = []
    evidence: list[str] = []

    for p in required:
        obj, err = _load_json(p)
        if obj is None:
            findings.append(f"{p.name}: {err}")
            continue
        loaded[p.name] = obj
        evidence.append(str(p.relative_to(repo)))

    if len(loaded) != len(required):
        return _unknown_payload(start, end, env, findings, evidence)

    timeline: list[dict[str, Any]] = []
    suspected: list[str] = ["fallback_mode: synthesized timeline from SSOT component files"]

    fresh = loaded["freshness_table.json"]
    f_rows = fresh.get("rows") or fresh.get("table") or []
    non_ok = [r for r in f_rows if isinstance(r, dict) and str(r.get("status", "UNKNOWN")).upper() != "OK"] if isinstance(f_rows, list) else []
    if non_ok:
        suspected.append(f"Freshness non-OK rows: {len(non_ok)}")

    cov = loaded["coverage_matrix_latest.json"]
    totals = cov.get("totals") if isinstance(cov.get("totals"), dict) else {}
    done = int(totals.get("done", 0) or 0)
    total = int(totals.get("total", done) or done)
    if total > 0 and done < total:
        suspected.append(f"Coverage incomplete: {done}/{total}")

    reg = loaded["regime_monitor_latest.json"]
    reg_status = str(reg.get("overall") or reg.get("status") or reg.get("overall_status") or "UNKNOWN").upper()
    if reg_status in {"WARN", "FAIL"}:
        reason = reg.get("reason")
        suspected.append(f"Regime monitor {reg_status}: {reason}")

    brk = loaded["brake_health_latest.json"]
    brk_status = str(brk.get("status") or "UNKNOWN").upper()
    if brk_status in {"WARN", "FAIL"}:
        suspected.append(f"Brake status {brk_status}")

    for name in [
        "freshness_table.json",
        "coverage_matrix_latest.json",
        "brake_health_latest.json",
        "regime_monitor_latest.json",
    ]:
        obj = loaded[name]
        ts = obj.get("ts_utc") or obj.get("generated_utc") or obj.get("timestamp_utc")
        timeline.append(
            {
                "ts": ts,
                "source": f"data/state/{name}",
                "event": f"Loaded SSOT component: {name}",
                "evidence_ref": f"data/state/{name}",
            }
        )

    status = "OK" if not suspected or suspected == ["fallback_mode: synthesized timeline from SSOT component files"] else "WARN"
    return {
        "summary": {
            "status": status,
            "report_only": True,
            "env": env,
            "time_range": {"start": start, "end": end},
            "refresh_hint": REFRESH_HINT,
            "source_mode": "ssot_fallback",
        },
        "timeline": timeline,
        "suspected_root_causes": suspected,
        "next_questions": [
            "Do fallback component timestamps align across files?",
            f"Run: {REFRESH_HINT}" if status != "OK" else "Any policy threshold changes within the window?",
        ],
    }


def build_incident_timeline(
    repo: Path,
    start: str,
    end: str,
    env: str,
    keywords: str | None = None,
    services: str | None = None,
) -> dict[str, Any]:
    """Build SSOT-only incident timeline payload."""
    payload: dict[str, Any]
    health, err = _load_json(repo / "data/state/system_health_latest.json")
    if health is not None:
        payload = _build_from_health_pack(repo, health, start, end, env)
    else:
        payload = _build_from_fallback(repo, start, end, env)

    kw = _split_csv(keywords)
    svc = _split_csv(services)
    if kw:
        payload["next_questions"].append(f"Keyword focus: {', '.join(kw)}")
    if svc:
        payload["next_questions"].append(f"Service focus: {', '.join(svc)}")

    return payload
