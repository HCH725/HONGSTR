import json
from pathlib import Path

from research.loop import leaderboard as lb


def test_entry_from_summary_keeps_direction_and_variant(tmp_path: Path):
    run_dir = tmp_path / "runA"
    run_dir.mkdir(parents=True)

    summary = {
        "candidate_id": "cand_short_01",
        "strategy_id": "supertrend_v2",
        "family": "trend",
        "direction": "SHORT",
        "variant": "atr_follow",
        "sharpe": 0.88,
        "max_drawdown": -0.12,
        "trades_count": 18,
        "timestamp": "2026-02-27T00:00:00+00:00",
        "status": "SUCCESS",
    }
    gate = {"overall": "PASS", "final_score": 104.3}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "gate.json").write_text(json.dumps(gate), encoding="utf-8")

    entry = lb._entry_from_summary(run_dir / "summary.json")
    assert entry is not None
    assert entry["direction"] == "SHORT"
    assert entry["variant"] == "atr_follow"
    assert entry["final_score"] == 104.3
