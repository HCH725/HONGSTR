"""
Executable overfit-governance gates (aggressive / yield-first, report_only).

This module evaluates research candidates weekly and emits:
- hard-gate decisions (pass/fail with reasons)
- soft-score ranking
- promote/demote/watchlist recommendations
- markdown weekly report under reports/ (runtime artifact, not committed)
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


HARD_GATES = {
    "min_oos_sharpe": 0.75,
    "max_drawdown": -0.25,
    "max_overfit_ratio": 2.20,
}

SOFT_SCORE_CFG = {
    "promote_cutoff": 82.0,
    "watchlist_cutoff": 60.0,
    "weights": {
        "oos_sharpe": 100.0,
        "total_return": 100.0,
        "drawdown_penalty": 28.0,
        "overfit_penalty": 35.0,
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _calc_overfit_ratio(is_sharpe: float, oos_sharpe: float) -> float:
    if oos_sharpe <= 0.0:
        return 99.0
    return is_sharpe / oos_sharpe


def _evaluate_hard_gates(row: Dict[str, Any]) -> Dict[str, Any]:
    oos_sharpe = _to_float(row.get("oos_sharpe"))
    oos_mdd = _to_float(row.get("oos_mdd"))
    is_sharpe = _to_float(row.get("is_sharpe"))
    overfit_ratio = _calc_overfit_ratio(is_sharpe, oos_sharpe)

    checks = {
        "oos_sharpe": {
            "pass": oos_sharpe >= HARD_GATES["min_oos_sharpe"],
            "value": round(oos_sharpe, 4),
            "threshold": HARD_GATES["min_oos_sharpe"],
            "operator": ">=",
        },
        "max_drawdown": {
            "pass": oos_mdd >= HARD_GATES["max_drawdown"],
            "value": round(oos_mdd, 4),
            "threshold": HARD_GATES["max_drawdown"],
            "operator": ">=",
        },
        "overfit_ratio": {
            "pass": overfit_ratio <= HARD_GATES["max_overfit_ratio"],
            "value": round(overfit_ratio, 4),
            "threshold": HARD_GATES["max_overfit_ratio"],
            "operator": "<=",
        },
    }
    failed = [name for name, c in checks.items() if not c["pass"]]
    return {"pass": len(failed) == 0, "checks": checks, "failed": failed}


def _soft_score(row: Dict[str, Any]) -> float:
    w = SOFT_SCORE_CFG["weights"]
    oos_sharpe = _to_float(row.get("oos_sharpe"))
    total_return = _to_float(row.get("oos_return", row.get("total_return", 0.0)))
    oos_mdd = _to_float(row.get("oos_mdd"))
    is_sharpe = _to_float(row.get("is_sharpe"))
    overfit_ratio = _calc_overfit_ratio(is_sharpe, oos_sharpe)

    score = 0.0
    score += oos_sharpe * w["oos_sharpe"]
    score += total_return * w["total_return"]
    score -= abs(min(0.0, oos_mdd)) * w["drawdown_penalty"]
    score -= max(0.0, overfit_ratio - 1.0) * w["overfit_penalty"]
    return round(score, 4)


def _recommend(hard_gate_passed: bool, soft_score: float) -> str:
    if not hard_gate_passed:
        return "demote"
    if soft_score >= SOFT_SCORE_CFG["promote_cutoff"]:
        return "promote"
    if soft_score >= SOFT_SCORE_CFG["watchlist_cutoff"]:
        return "watchlist"
    return "demote"


def evaluate_weekly_governance(
    entries: Iterable[Dict[str, Any]],
    *,
    week_id: str,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    rows = list(entries)
    evaluated: List[Dict[str, Any]] = []
    for row in rows:
        hard = _evaluate_hard_gates(row)
        score = _soft_score(row)
        decision = _recommend(hard["pass"], score)
        evaluated.append(
            {
                "strategy_id": str(row.get("strategy_id") or row.get("experiment_id") or "unknown"),
                "direction": str(row.get("direction", "long")).upper(),
                "variant": str(row.get("variant", "base")),
                "oos_sharpe": _to_float(row.get("oos_sharpe")),
                "oos_mdd": _to_float(row.get("oos_mdd")),
                "oos_return": _to_float(row.get("oos_return", row.get("total_return", 0.0))),
                "is_sharpe": _to_float(row.get("is_sharpe")),
                "hard_gates": hard,
                "soft_score": score,
                "recommendation": decision,
                "reasons": hard["failed"],
            }
        )

    ranked = sorted(evaluated, key=lambda item: item["soft_score"], reverse=True)
    summary = {
        "total": len(ranked),
        "promote": sum(1 for item in ranked if item["recommendation"] == "promote"),
        "demote": sum(1 for item in ranked if item["recommendation"] == "demote"),
        "watchlist": sum(1 for item in ranked if item["recommendation"] == "watchlist"),
    }

    return {
        "schema_version": "governance_weekly_v1",
        "week_id": week_id,
        "generated_at": generated_at or _utc_now(),
        "report_only": True,
        "actions": [],
        "hard_gates": dict(HARD_GATES),
        "soft_scoring": dict(SOFT_SCORE_CFG),
        "summary": summary,
        "recommendations": ranked,
    }


def build_quant_specialist_weekly_check(
    entries: Iterable[Dict[str, Any]],
    *,
    week_id: str,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    payload = evaluate_weekly_governance(entries, week_id=week_id, generated_at=generated_at)
    payload["skill"] = "overfit_governance_weekly_check"
    payload["constraints"] = ["read_only", "report_only"]
    payload["refresh_hint"] = "bash scripts/refresh_state.sh"
    return payload


def render_weekly_governance_markdown(payload: Dict[str, Any]) -> str:
    summary = payload.get("summary", {})
    recs = payload.get("recommendations", [])
    lines = [
        f"# Weekly Overfit Governance Report ({payload.get('week_id', 'unknown_week')})",
        "",
        f"- GeneratedAt: `{payload.get('generated_at', '')}`",
        "- Mode: `report_only` (`actions=[]`)",
        f"- HardGates: `{json.dumps(payload.get('hard_gates', {}), ensure_ascii=False)}`",
        "",
        "## Summary",
        f"- Total Candidates: `{summary.get('total', 0)}`",
        f"- Promote: `{summary.get('promote', 0)}`",
        f"- Watchlist: `{summary.get('watchlist', 0)}`",
        f"- Demote: `{summary.get('demote', 0)}`",
        "",
        "## Recommendations",
        "| strategy_id | direction | variant | soft_score | recommendation | hard_gate_pass |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in recs:
        lines.append(
            "| {strategy_id} | {direction} | {variant} | {soft_score:.2f} | {recommendation} | {hard_pass} |".format(
                strategy_id=row.get("strategy_id", "unknown"),
                direction=row.get("direction", "LONG"),
                variant=row.get("variant", "base"),
                soft_score=float(row.get("soft_score", 0.0)),
                recommendation=row.get("recommendation", "watchlist"),
                hard_pass="PASS" if row.get("hard_gates", {}).get("pass") else "FAIL",
            )
        )
    lines.extend(
        [
            "",
            "## Policy",
            "- Hard gate failures are never auto-promoted.",
            "- Soft score ranking is used for yield-first ordering among hard-gate pass candidates.",
            "- Suggestions only (`promote/demote/watchlist`); no automatic system mutation.",
        ]
    )
    return "\n".join(lines)


def write_weekly_governance_report(
    payload: Dict[str, Any],
    reports_root: Path,
    *,
    filename: Optional[str] = None,
) -> Path:
    reports_root.mkdir(parents=True, exist_ok=True)
    week_id = str(payload.get("week_id", "unknown_week"))
    out_name = filename or f"governance_{week_id}.md"
    out_path = reports_root / out_name
    out_path.write_text(render_weekly_governance_markdown(payload), encoding="utf-8")
    return out_path
