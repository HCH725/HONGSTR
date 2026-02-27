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

    ranked = sorted(entries, key=lambda x: (_sort_metric(x.get("final_score")), _sort_metric(x.get("oos_sharpe"))), reverse=True)
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

    sharpe = _as_float(data.get("sharpe", data.get("oos_sharpe")), None)

    gate_payload = _load_gate(path.parent / "gate.json")
    gate_overall = gate_payload.get("overall") if gate_payload else "UNKNOWN"
    final_score = _as_float(gate_payload.get("final_score") if gate_payload else data.get("final_score"), None)
    oos_mdd = _as_float(data.get("max_drawdown", data.get("oos_mdd")), None)
    is_sharpe = _as_float(data.get("is_sharpe"), None)
    trades_count = _as_int(data.get("trades_count"))

    metrics_status = "OK"
    metrics_reason = ""
    if sharpe is None or oos_mdd is None:
        metrics_status = "UNKNOWN"
        metrics_reason = "missing_slice_metrics"

    return {
        "experiment_id": data.get("experiment_id") or data.get("candidate_id") or data.get("strategy_id") or path.parent.name,
        "candidate_id": data.get("candidate_id") or path.parent.name,
        "strategy_id": data.get("strategy_id", "unknown"),
        "family": data.get("family", "unknown"),
        "direction": data.get("direction", "LONG"),
        "variant": data.get("variant", "base"),
        "regime": data.get("regime", data.get("regime_slice", "ALL")),
        "regime_slice": data.get("regime_slice", data.get("regime", "ALL")),
        "regime_window_start_utc": data.get("regime_window_start_utc"),
        "regime_window_end_utc": data.get("regime_window_end_utc"),
        "oos_sharpe": sharpe,
        "oos_mdd": oos_mdd,
        "is_sharpe": is_sharpe,
        "trades_count": trades_count,
        "final_score": final_score,
        "gate_overall": gate_overall,
        "status": data.get("status", "UNKNOWN"),
        "metrics_status": metrics_status,
        "metrics_reason": metrics_reason,
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
    sharpe = _as_float(data.get("oos_sharpe"), None)
    mdd = _as_float(data.get("oos_mdd"), None)
    final_score = _as_float(data.get("final_score"), None)
    is_sharpe = _as_float(data.get("is_sharpe"), None)
    trades_count = _as_int(data.get("trades_count"))
    metrics_status = "OK"
    metrics_reason = ""
    if sharpe is None or mdd is None:
        metrics_status = "UNKNOWN"
        metrics_reason = "missing_slice_metrics"

    return {
        "experiment_id": data.get("experiment_id", exp_id_stem),
        "candidate_id": data.get("candidate_id", exp_id_stem),
        "strategy_id": data.get("strategy_id", exp_id_stem),
        "family": data.get("family", "legacy"),
        "direction": data.get("direction", "LONG"),
        "variant": data.get("variant", "legacy"),
        "regime": data.get("regime", data.get("regime_slice", "ALL")),
        "regime_slice": data.get("regime_slice", data.get("regime", "ALL")),
        "regime_window_start_utc": data.get("regime_window_start_utc"),
        "regime_window_end_utc": data.get("regime_window_end_utc"),
        "oos_sharpe": sharpe,
        "oos_mdd": mdd,
        "is_sharpe": is_sharpe,
        "trades_count": trades_count,
        "final_score": final_score,
        "gate_overall": data.get("gate_overall", "UNKNOWN"),
        "status": data.get("status", "UNKNOWN"),
        "metrics_status": metrics_status,
        "metrics_reason": metrics_reason,
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


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def _sort_metric(value: Any) -> float:
    parsed = _as_float(value, None)
    if parsed is None:
        return float("-inf")
    return float(parsed)


def _fmt_metric(value: Any, *, pct: bool = False) -> str:
    parsed = _as_float(value, None)
    if parsed is None:
        return "UNKNOWN"
    return f"{parsed:.2%}" if pct else f"{parsed:.2f}"


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    path = save_leaderboard()
    print(f"Leaderboard written to {path}")
    board = json.loads(path.read_text(encoding="utf-8"))
    for i, e in enumerate(board.get("entries", []), 1):
        score = _fmt_metric(e.get("final_score"))
        sharpe = _fmt_metric(e.get("oos_sharpe"))
        mdd = _fmt_metric(e.get("oos_mdd"), pct=True)
        print(
            f"#{i} {e['candidate_id']} score={score} "
            f"sharpe={sharpe} "
            f"mdd={mdd} regime={e.get('regime_slice', 'ALL')}"
        )
    sys.exit(0)
