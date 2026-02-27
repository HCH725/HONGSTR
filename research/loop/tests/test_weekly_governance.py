import json
from pathlib import Path

from research.loop.weekly_governance import generate_weekly_quant_checklist


def test_weekly_checklist_generation(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data/state/_research").mkdir(parents=True)
    (repo / "data/state").mkdir(parents=True, exist_ok=True)

    (repo / "data/state/system_health_latest.json").write_text(
        json.dumps({"ssot_status": "OK"}),
        encoding="utf-8",
    )
    (repo / "data/state/strategy_pool_summary.json").write_text(
        json.dumps(
            {
                "leaderboard": [
                    {"id": "cand_a", "score": 96.0},
                    {"id": "cand_b", "score": 62.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    (repo / "data/state/_research/leaderboard.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "candidate_id": "cand_c",
                        "final_score": 45.0,
                        "oos_sharpe": 0.3,
                        "direction": "SHORT",
                        "gate_overall": "PASS",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    out = generate_weekly_quant_checklist(repo)
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["counts"]["candidate_total"] >= 2
    assert "short_coverage" in out["counts"]
    assert out["counts"]["short_coverage"]["candidate_count"] >= 1
    assert out["counts"]["short_coverage"]["gate_passed_count"] >= 1

    json_path = repo / out["outputs"]["json"]
    md_path = repo / out["outputs"]["markdown"]
    assert json_path.exists()
    assert md_path.exists()


def test_weekly_checklist_watchlist_floor(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data/state/_research").mkdir(parents=True)
    (repo / "data/state").mkdir(parents=True, exist_ok=True)
    (repo / "research/policy").mkdir(parents=True, exist_ok=True)

    (repo / "research/policy/overfit_gates_aggressive.json").write_text(
        json.dumps({"watchlist": {"min_candidates": 1}}),
        encoding="utf-8",
    )
    (repo / "data/state/system_health_latest.json").write_text(json.dumps({"ssot_status": "WARN"}), encoding="utf-8")
    (repo / "data/state/strategy_pool_summary.json").write_text(
        json.dumps({"leaderboard": [{"id": "only_demote", "score": 20.0}]}),
        encoding="utf-8",
    )
    (repo / "data/state/_research/leaderboard.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

    out = generate_weekly_quant_checklist(repo)
    assert out["counts"]["watchlist"] >= 1
    assert out["recommendations"]["watchlist"]


def test_weekly_checklist_short_coverage_best_entry(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data/state/_research").mkdir(parents=True)
    (repo / "data/state").mkdir(parents=True, exist_ok=True)

    (repo / "data/state/system_health_latest.json").write_text(json.dumps({"ssot_status": "OK"}), encoding="utf-8")
    (repo / "data/state/strategy_pool_summary.json").write_text(json.dumps({"leaderboard": []}), encoding="utf-8")
    (repo / "data/state/_research/leaderboard.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"candidate_id": "s_short_1", "final_score": 92.0, "direction": "SHORT", "gate_overall": "PASS"},
                    {"candidate_id": "s_short_2", "final_score": 88.0, "direction": "SHORT", "gate_overall": "FAIL"},
                    {"candidate_id": "s_long_1", "final_score": 95.0, "direction": "LONG", "gate_overall": "PASS"},
                ]
            }
        ),
        encoding="utf-8",
    )

    out = generate_weekly_quant_checklist(repo)
    short_cov = out["counts"]["short_coverage"]
    assert short_cov["candidate_count"] == 2
    assert short_cov["gate_passed_count"] == 1
    assert short_cov["best_entry"]["id"] == "s_short_1"
