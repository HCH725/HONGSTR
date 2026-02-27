"""
HONGSTR Research Leaderboard
Ranks completed candidates primarily by gate final_score, then OOS Sharpe.
Reads from reports/research/ and writes to data/state/_research/leaderboard.json.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_ROOT = REPO_ROOT / "reports/research"
LEADERBOARD_PATH = REPO_ROOT / "data/state/_research/leaderboard.json"

logger = logging.getLogger("research_leaderboard")


def build_leaderboard(top_n: int = 10) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not REPORTS_ROOT.exists():
        return entries

    seen_keys: set[str] = set()

    for summary_path in sorted(REPORTS_ROOT.rglob("summary.json")):
        entry = _entry_from_summary(summary_path)
        if not entry:
            continue
        key = str(entry.get("candidate_id") or entry.get("experiment_id"))
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        entries.append(entry)

    # Backward compatibility with legacy *_results.json artifacts
    for results_file in sorted(REPORTS_ROOT.rglob("*_results.json")):
        entry = _entry_from_results(results_file)
        if not entry:
            continue
        key = str(entry.get("candidate_id") or entry.get("experiment_id"))
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        entries.append(entry)

    ranked = sorted(
        entries,
        key=lambda x: (float(x.get("final_score", 0.0)), float(x.get("oos_sharpe", 0.0))),
        reverse=True,
    )
    return ranked[:top_n]


def save_leaderboard(top_n: int = 10) -> Path:
    board = build_leaderboard(top_n=top_n)
    direction_counts = _direction_counts(board)
    short_coverage = _short_coverage(board)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ranked_by": ["final_score_desc", "oos_sharpe_desc"],
        "top_n": top_n,
        "columns": [
            "candidate_id",
            "strategy_id",
            "family",
            "direction",
            "variant",
            "gate_overall",
            "final_score",
            "oos_sharpe",
            "oos_mdd",
        ],
        "direction_counts": direction_counts,
        "short_coverage": short_coverage,
        "entries": board,
    }
    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Leaderboard saved: %s entries -> %s", len(board), LEADERBOARD_PATH)
    return LEADERBOARD_PATH


def _entry_from_summary(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse %s: %s", path, exc)
        return None

    if not isinstance(data, dict):
        return None

    sharpe = _as_float(data.get("sharpe", data.get("oos_sharpe")), None)
    if sharpe is None:
        return None

    gate_payload = _load_gate(path.parent / "gate.json")
    gate_overall = gate_payload.get("overall") if gate_payload else "UNKNOWN"
    final_score = _as_float(gate_payload.get("final_score") if gate_payload else data.get("final_score"), 0.0)

    return {
        "experiment_id": data.get("experiment_id") or data.get("candidate_id") or data.get("strategy_id") or path.parent.name,
        "candidate_id": data.get("candidate_id") or path.parent.name,
        "strategy_id": data.get("strategy_id", "unknown"),
        "family": data.get("family", "unknown"),
        "direction": _direction_label(data.get("direction")),
        "variant": data.get("variant", "base"),
        "oos_sharpe": sharpe,
        "oos_mdd": _as_float(data.get("max_drawdown", data.get("oos_mdd")), 0.0),
        "is_sharpe": _as_float(data.get("is_sharpe"), 0.0),
        "trades_count": int(_as_float(data.get("trades_count"), 0.0)),
        "final_score": final_score,
        "gate_overall": gate_overall,
        "status": data.get("status", "UNKNOWN"),
        "timestamp": data.get("timestamp", ""),
        "report_dir": str(path.parent),
    }


def _entry_from_results(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not parse %s: %s", path, exc)
        return None

    if not isinstance(data, dict):
        return None
    if "oos_sharpe" not in data:
        return None

    exp_id_stem = path.stem.replace("_results", "")
    return {
        "experiment_id": data.get("experiment_id", exp_id_stem),
        "candidate_id": data.get("candidate_id", exp_id_stem),
        "strategy_id": data.get("strategy_id", exp_id_stem),
        "family": data.get("family", "legacy"),
        "direction": _direction_label(data.get("direction")),
        "variant": data.get("variant", "legacy"),
        "oos_sharpe": _as_float(data.get("oos_sharpe"), 0.0),
        "oos_mdd": _as_float(data.get("oos_mdd"), 0.0),
        "is_sharpe": _as_float(data.get("is_sharpe"), 0.0),
        "trades_count": int(_as_float(data.get("trades_count"), 0.0)),
        "final_score": _as_float(data.get("final_score"), 0.0),
        "gate_overall": data.get("gate_overall", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "timestamp": data.get("timestamp", ""),
        "report_dir": str(path.parent),
    }


def _load_gate(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _as_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default


def _direction_label(value: Any) -> str:
    direction = str(value or "UNKNOWN").strip().upper()
    if not direction:
        return "UNKNOWN"
    return direction


def _direction_counts(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        direction = _direction_label(entry.get("direction"))
        counts[direction] = counts.get(direction, 0) + 1
    return counts


def _short_coverage(entries: list[dict[str, Any]]) -> dict[str, Any]:
    shorts = [e for e in entries if _direction_label(e.get("direction")) == "SHORT"]
    passed = [
        e for e in shorts if str(e.get("gate_overall", e.get("status", "UNKNOWN"))).strip().upper() == "PASS"
    ]
    best = (
        sorted(
            shorts,
            key=lambda x: (float(x.get("final_score", 0.0)), float(x.get("oos_sharpe", 0.0))),
            reverse=True,
        )[0]
        if shorts
        else None
    )
    return {
        "candidate_count": len(shorts),
        "gate_passed_count": len(passed),
        "best_entry": _compact_entry(best),
    }


def _compact_entry(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not entry:
        return None
    return {
        "candidate_id": entry.get("candidate_id"),
        "strategy_id": entry.get("strategy_id"),
        "family": entry.get("family"),
        "direction": _direction_label(entry.get("direction")),
        "variant": entry.get("variant"),
        "gate_overall": str(entry.get("gate_overall", "UNKNOWN")).upper(),
        "final_score": float(entry.get("final_score", 0.0)),
        "oos_sharpe": float(entry.get("oos_sharpe", 0.0)),
        "oos_mdd": float(entry.get("oos_mdd", 0.0)),
        "report_dir": entry.get("report_dir"),
    }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = save_leaderboard()
    print(f"Leaderboard written to {path}")
    board = json.loads(path.read_text(encoding="utf-8"))
    for i, e in enumerate(board.get("entries", []), 1):
        print(
            f"#{i} {e['candidate_id']} direction={e.get('direction', 'UNKNOWN')} "
            f"score={e['final_score']:.2f} "
            f"sharpe={e['oos_sharpe']:.2f} mdd={e['oos_mdd']:.2%}"
        )
    sys.exit(0)
