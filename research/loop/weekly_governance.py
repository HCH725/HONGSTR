from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REFRESH_HINT = "bash scripts/refresh_state.sh"


def generate_weekly_quant_checklist(
    repo_root: Path,
    *,
    recent_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    now = datetime.now(timezone.utc)
    year, week, _ = now.isocalendar()

    out_dir = root / f"reports/research/governance/{year}_W{week:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    health = _load_json(root / "data/state/system_health_latest.json")
    pool_summary = _load_json(root / "data/state/strategy_pool_summary.json")
    leaderboard = _load_json(root / "data/state/_research/leaderboard.json")

    candidate_rows = _extract_candidates(pool_summary, leaderboard, recent_results or [])
    sorted_rows = sorted(candidate_rows, key=lambda x: float(x.get("score", 0.0)), reverse=True)

    policy = _load_json(root / "research/policy/overfit_gates_aggressive.json") or {}
    watch_floor = max(1, _as_int((policy.get("watchlist", {}) or {}).get("min_candidates"), 1))
    _apply_watchlist_floor(sorted_rows, watch_floor)

    promote = [r["id"] for r in sorted_rows if r.get("recommendation") == "PROMOTE"][:3]
    demote = [r["id"] for r in sorted_rows if r.get("recommendation") == "DEMOTE"]
    watchlist = [r["id"] for r in sorted_rows if r.get("recommendation") == "WATCHLIST"]

    if not sorted_rows:
        status = "UNKNOWN"
    elif promote:
        status = "OK"
    else:
        status = "WARN"

    payload = {
        "generated_utc": now.isoformat(),
        "iso_week": f"{year}-W{week:02d}",
        "status": status,
        "report_only": True,
        "actions": [],
        "refresh_hint": REFRESH_HINT,
        "sources": {
            "system_health_latest": _exists_rel(root, "data/state/system_health_latest.json"),
            "strategy_pool_summary": _exists_rel(root, "data/state/strategy_pool_summary.json"),
            "research_leaderboard": _exists_rel(root, "data/state/_research/leaderboard.json"),
        },
        "counts": {
            "candidate_total": len(sorted_rows),
            "promote": len(promote),
            "demote": len(demote),
            "watchlist": len(watchlist),
        },
        "recommendations": {
            "promote": promote,
            "demote": demote,
            "watchlist": watchlist,
        },
        "top_candidates": sorted_rows[:10],
        "ssot_status": (health or {}).get("ssot_status", "UNKNOWN"),
    }

    json_path = out_dir / "weekly_quant_checklist.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_lines = [
        f"# Weekly Quant Checklist ({payload['iso_week']})",
        "",
        f"- generated_utc: {payload['generated_utc']}",
        f"- status: {payload['status']}",
        "- report_only: true",
        "- actions: []",
        f"- refresh_hint: `{REFRESH_HINT}`",
        f"- ssot_status: {payload['ssot_status']}",
        "",
        "## Recommendations",
        f"- promote: {', '.join(promote) if promote else 'none'}",
        f"- demote: {', '.join(demote) if demote else 'none'}",
        f"- watchlist: {', '.join(watchlist) if watchlist else 'none'}",
        "",
        "## Top Candidates",
        "| id | score | recommendation | regime_slice | regime_window_utc | reason |",
        "|---|---:|---|---|---|---|",
    ]
    for row in sorted_rows[:10]:
        start = str(row.get("regime_window_start_utc") or "")
        end = str(row.get("regime_window_end_utc") or "")
        window = f"[{start},{end})" if start and end else "ALL/default"
        md_lines.append(
            f"| {row.get('id')} | {float(row.get('score', 0.0)):.2f} | {row.get('recommendation')} | "
            f"{row.get('regime_slice', 'ALL')} | {window} | {row.get('reason')} |"
        )

    md_path = out_dir / "weekly_quant_checklist.md"
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    payload["outputs"] = {
        "json": str(json_path.relative_to(root)),
        "markdown": str(md_path.relative_to(root)),
    }
    return payload


def _extract_candidates(
    pool_summary: dict[str, Any] | None,
    leaderboard: dict[str, Any] | None,
    recent_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if isinstance(pool_summary, dict):
        for c in pool_summary.get("leaderboard", []) or []:
            cid = str(c.get("id") or "").strip()
            if not cid:
                continue
            score = _as_float(c.get("score"), 0.0)
            recommendation = "PROMOTE" if score >= 90.0 else "WATCHLIST" if score >= 55.0 else "DEMOTE"
            rows.append(
                {
                    "id": cid,
                    "score": score,
                    "recommendation": recommendation,
                    "reason": "strategy_pool_summary",
                    "regime_slice": _normalize_regime_slice(c.get("regime_slice") or c.get("regime")),
                    "regime_window_start_utc": c.get("regime_window_start_utc"),
                    "regime_window_end_utc": c.get("regime_window_end_utc"),
                    "regime_rationale": str(c.get("regime_rationale") or "default_all_no_slice"),
                    "regime_rationale_zh": str(c.get("regime_rationale_zh") or ""),
                }
            )

    if isinstance(leaderboard, dict):
        for e in leaderboard.get("entries", []) or []:
            cid = str(e.get("candidate_id") or e.get("experiment_id") or "").strip()
            if not cid or any(r["id"] == cid for r in rows):
                continue
            score = _as_float(e.get("final_score"), _as_float(e.get("oos_sharpe"), 0.0) * 40.0)
            recommendation = "PROMOTE" if score >= 90.0 else "WATCHLIST" if score >= 55.0 else "DEMOTE"
            rows.append(
                {
                    "id": cid,
                    "score": score,
                    "recommendation": recommendation,
                    "reason": "research_leaderboard",
                    "regime_slice": _normalize_regime_slice(e.get("regime_slice") or e.get("regime")),
                    "regime_window_start_utc": e.get("regime_window_start_utc"),
                    "regime_window_end_utc": e.get("regime_window_end_utc"),
                    "regime_rationale": str(e.get("regime_rationale") or "default_all_no_slice"),
                    "regime_rationale_zh": str(e.get("regime_rationale_zh") or ""),
                }
            )

    for e in recent_results:
        cid = str(e.get("id") or e.get("candidate_id") or e.get("experiment_id") or "").strip()
        if not cid or any(r["id"] == cid for r in rows):
            continue
        score = _as_float(e.get("score"), 0.0)
        recommendation = str(e.get("recommendation") or "WATCHLIST").upper()
        rows.append(
            {
                "id": cid,
                "score": score,
                "recommendation": recommendation,
                "reason": "recent_results",
                "regime_slice": _normalize_regime_slice(e.get("regime_slice") or e.get("regime")),
                "regime_window_start_utc": e.get("regime_window_start_utc"),
                "regime_window_end_utc": e.get("regime_window_end_utc"),
                "regime_rationale": str(e.get("regime_rationale") or "default_all_no_slice"),
                "regime_rationale_zh": str(e.get("regime_rationale_zh") or ""),
            }
        )

    return rows


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _exists_rel(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)


def _normalize_regime_slice(v: Any) -> str:
    value = str(v or "ALL").upper().strip()
    return value if value in {"ALL", "BULL", "BEAR", "SIDEWAYS"} else "ALL"


def _apply_watchlist_floor(rows: list[dict[str, Any]], floor: int) -> None:
    if floor <= 0 or not rows:
        return
    watch_count = sum(1 for r in rows if str(r.get("recommendation", "")).upper() == "WATCHLIST")
    promote_count = sum(1 for r in rows if str(r.get("recommendation", "")).upper() == "PROMOTE")
    if promote_count > 0 or watch_count >= floor:
        return

    needed = floor - watch_count
    for row in rows:
        if needed <= 0:
            break
        if str(row.get("recommendation", "")).upper() == "WATCHLIST":
            continue
        row["recommendation"] = "WATCHLIST"
        row["reason"] = f"{row.get('reason', 'unknown')}+watchlist_floor"
        needed -= 1
