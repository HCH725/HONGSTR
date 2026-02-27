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

    ranked = sorted(entries, key=_rank_key, reverse=True)
    return ranked[:top_n]


def save_leaderboard(top_n: int = 10) -> Path:
    board = build_leaderboard(top_n=top_n)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ranked_by": ["final_score_desc", "oos_sharpe_desc"],
        "top_n": top_n,
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

    status = str(data.get("status", "UNKNOWN")).upper()
    sharpe = _as_optional_float(data.get("sharpe", data.get("oos_sharpe")))
    oos_mdd = _as_optional_float(data.get("max_drawdown", data.get("oos_mdd")))
    is_sharpe = _as_optional_float(data.get("is_sharpe"))
    trades_count = _as_optional_int(data.get("trades_count"))
    gate_payload = _load_gate(path.parent / "gate.json")
    gate_overall = str(gate_payload.get("overall") if gate_payload else data.get("gate_overall", "UNKNOWN")).upper()
    final_score = _as_optional_float(gate_payload.get("final_score") if gate_payload else data.get("final_score"))
    if status == "DRY_RUN":
        sharpe = None
        oos_mdd = None
        is_sharpe = None
        trades_count = None
        final_score = None
    metrics_status, metrics_reason = _metric_status(
        status=status,
        final_score=final_score,
        oos_sharpe=sharpe,
        oos_mdd=oos_mdd,
    )

    return {
        "experiment_id": data.get("experiment_id") or data.get("candidate_id") or data.get("strategy_id") or path.parent.name,
        "candidate_id": data.get("candidate_id") or path.parent.name,
        "strategy_id": data.get("strategy_id", "unknown"),
        "family": data.get("family", "unknown"),
        "direction": _direction_label(data.get("direction")),
        "variant": data.get("variant", "base"),
        "oos_sharpe": sharpe,
        "oos_mdd": oos_mdd,
        "is_sharpe": is_sharpe,
        "trades_count": trades_count,
        "final_score": final_score,
        "gate_overall": gate_overall,
        "status": status,
        "metrics_status": metrics_status,
        "metrics_unavailable_reason": metrics_reason,
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

    exp_id_stem = path.stem.replace("_results", "")
    status = str(data.get("status", "UNKNOWN")).upper()
    final_score = _as_optional_float(data.get("final_score"))
    oos_sharpe = _as_optional_float(data.get("oos_sharpe"))
    oos_mdd = _as_optional_float(data.get("oos_mdd"))
    is_sharpe = _as_optional_float(data.get("is_sharpe"))
    trades_count = _as_optional_int(data.get("trades_count"))
    if status == "DRY_RUN":
        final_score = None
        oos_sharpe = None
        oos_mdd = None
        is_sharpe = None
        trades_count = None
    metrics_status, metrics_reason = _metric_status(
        status=status,
        final_score=final_score,
        oos_sharpe=oos_sharpe,
        oos_mdd=oos_mdd,
    )
    return {
        "experiment_id": data.get("experiment_id", exp_id_stem),
        "candidate_id": data.get("candidate_id", exp_id_stem),
        "strategy_id": data.get("strategy_id", exp_id_stem),
        "family": data.get("family", "legacy"),
        "direction": _direction_label(data.get("direction")),
        "variant": data.get("variant", "legacy"),
        "oos_sharpe": oos_sharpe,
        "oos_mdd": oos_mdd,
        "is_sharpe": is_sharpe,
        "trades_count": trades_count,
        "final_score": final_score,
        "gate_overall": str(data.get("gate_overall", "UNKNOWN")).upper(),
        "status": status,
        "metrics_status": metrics_status,
        "metrics_unavailable_reason": metrics_reason,
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


def _as_optional_float(value: Any) -> float | None:
    return _as_float(value, None)


def _as_optional_int(value: Any) -> int | None:
    fval = _as_optional_float(value)
    if fval is None:
        return None
    return int(fval)


def _direction_label(value: Any) -> str:
    direction = str(value or "UNKNOWN").strip().upper()
    return direction if direction else "UNKNOWN"


def _metric_status(status: str, **metrics: float | None) -> tuple[str, str | None]:
    missing = [k for k, v in metrics.items() if v is None]
    if not missing:
        return "OK", None
    if status == "DRY_RUN":
        return "UNKNOWN", "dry_run_artifact"
    return "UNKNOWN", "missing_metrics:" + ",".join(sorted(missing))


def _rank_number(value: Any) -> float:
    val = _as_optional_float(value)
    if val is None:
        return float("-inf")
    return val


def _rank_key(entry: dict[str, Any]) -> tuple[float, float]:
    return (_rank_number(entry.get("final_score")), _rank_number(entry.get("oos_sharpe")))


def _fmt_number(value: Any, fmt: str = ".2f") -> str:
    val = _as_optional_float(value)
    if val is None:
        return "UNKNOWN"
    return format(val, fmt)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = save_leaderboard()
    print(f"Leaderboard written to {path}")
    board = json.loads(path.read_text(encoding="utf-8"))
    for i, e in enumerate(board.get("entries", []), 1):
        print(
            f"#{i} {e['candidate_id']} score={_fmt_number(e.get('final_score'))} "
            f"sharpe={_fmt_number(e.get('oos_sharpe'))} "
            f"mdd={_fmt_number(e.get('oos_mdd'), '.2%')} "
            f"metrics_status={e.get('metrics_status', 'UNKNOWN')}"
        )
    sys.exit(0)
