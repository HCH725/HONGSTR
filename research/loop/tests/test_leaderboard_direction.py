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


def test_entry_from_summary_regime_backward_compat(tmp_path: Path):
    run_dir = tmp_path / "runB"
    run_dir.mkdir(parents=True)

    summary = {
        "candidate_id": "cand_legacy_01",
        "strategy_id": "ema_cross_v3",
        "family": "trend",
        "direction": "LONG",
        "variant": "base",
        "sharpe": 0.65,
        "max_drawdown": -0.17,
        "trades_count": 11,
        "timestamp": "2026-02-27T00:00:00+00:00",
        "status": "SUCCESS",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "gate.json").write_text(json.dumps({"overall": "WARN"}), encoding="utf-8")

    entry = lb._entry_from_summary(run_dir / "summary.json")
    assert entry is not None
    assert entry["regime_slice"] == "ALL"
    assert entry["metrics_status"] == "OK"
