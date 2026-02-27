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


def test_save_leaderboard_includes_short_coverage(tmp_path: Path, monkeypatch):
    reports = tmp_path / "reports" / "research" / "20260227"
    run_short = reports / "cand_short_01"
    run_long = reports / "cand_long_01"
    run_short.mkdir(parents=True)
    run_long.mkdir(parents=True)

    (run_short / "summary.json").write_text(
        json.dumps(
            {
                "candidate_id": "cand_short_01",
                "strategy_id": "s_short",
                "family": "trend",
                "direction": "SHORT",
                "variant": "base",
                "sharpe": 0.9,
                "max_drawdown": -0.08,
                "timestamp": "2026-02-27T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (run_short / "gate.json").write_text(
        json.dumps({"overall": "PASS", "final_score": 101.5}),
        encoding="utf-8",
    )

    (run_long / "summary.json").write_text(
        json.dumps(
            {
                "candidate_id": "cand_long_01",
                "strategy_id": "s_long",
                "family": "trend",
                "direction": "LONG",
                "variant": "base",
                "sharpe": 0.7,
                "max_drawdown": -0.1,
                "timestamp": "2026-02-27T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    (run_long / "gate.json").write_text(
        json.dumps({"overall": "FAIL", "final_score": 45.0}),
        encoding="utf-8",
    )

    out_path = tmp_path / "data" / "state" / "_research" / "leaderboard.json"
    monkeypatch.setattr(lb, "REPORTS_ROOT", reports.parent)
    monkeypatch.setattr(lb, "LEADERBOARD_PATH", out_path)

    lb.save_leaderboard(top_n=10)
    payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert payload["direction_counts"]["SHORT"] == 1
    assert payload["short_coverage"]["candidate_count"] == 1
    assert payload["short_coverage"]["gate_passed_count"] == 1
    assert payload["short_coverage"]["best_entry"]["candidate_id"] == "cand_short_01"
