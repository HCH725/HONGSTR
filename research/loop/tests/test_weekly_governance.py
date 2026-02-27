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
        json.dumps({"entries": [{"candidate_id": "cand_c", "final_score": 45.0, "oos_sharpe": 0.3}]}),
        encoding="utf-8",
    )

    out = generate_weekly_quant_checklist(repo)
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["counts"]["candidate_total"] >= 2
    assert out["top_candidates"][0]["regime_slice"] in {"ALL", "BULL", "BEAR", "SIDEWAYS"}

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


def test_weekly_checklist_keeps_regime_slice_from_recent_results(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data/state/_research").mkdir(parents=True)
    (repo / "data/state").mkdir(parents=True, exist_ok=True)
    (repo / "data/state/system_health_latest.json").write_text(json.dumps({"ssot_status": "OK"}), encoding="utf-8")
    (repo / "data/state/strategy_pool_summary.json").write_text(json.dumps({"leaderboard": []}), encoding="utf-8")
    (repo / "data/state/_research/leaderboard.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

    out = generate_weekly_quant_checklist(
        repo,
        recent_results=[
            {
                "candidate_id": "cand_regime_bull",
                "score": 91.0,
                "recommendation": "PROMOTE",
                "regime_slice": "BULL",
                "regime_window_start_utc": "2026-01-01T00:00:00Z",
                "regime_window_end_utc": "2026-04-01T00:00:00Z",
            }
        ],
    )
    assert out["top_candidates"]
    top = out["top_candidates"][0]
    assert top["regime_slice"] == "BULL"
    assert top["regime_window_start_utc"] == "2026-01-01T00:00:00Z"
    assert top["regime_window_end_utc"] == "2026-04-01T00:00:00Z"
    assert top["regime_window_utc"] == ["2026-01-01T00:00:00Z", "2026-04-01T00:00:00Z"]


def test_weekly_checklist_keeps_same_candidate_different_slices(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "data/state/_research").mkdir(parents=True)
    (repo / "data/state").mkdir(parents=True, exist_ok=True)
    (repo / "data/state/system_health_latest.json").write_text(json.dumps({"ssot_status": "OK"}), encoding="utf-8")
    (repo / "data/state/strategy_pool_summary.json").write_text(json.dumps({"leaderboard": []}), encoding="utf-8")
    (repo / "data/state/_research/leaderboard.json").write_text(json.dumps({"entries": []}), encoding="utf-8")

    out = generate_weekly_quant_checklist(
        repo,
        recent_results=[
            {
                "candidate_id": "cand_mix",
                "strategy_id": "supertrend_v2",
                "direction": "LONG",
                "variant": "base",
                "score": 92.0,
                "recommendation": "PROMOTE",
                "regime_slice": "ALL",
            },
            {
                "candidate_id": "cand_mix",
                "strategy_id": "supertrend_v2",
                "direction": "LONG",
                "variant": "base",
                "score": 84.0,
                "recommendation": "WATCHLIST",
                "regime_slice": "BULL",
                "regime_window_start_utc": "2026-01-01T00:00:00Z",
                "regime_window_end_utc": "2026-04-01T00:00:00Z",
            },
        ],
    )
    tops = out["top_candidates"]
    assert len(tops) == 2
    assert {t["regime_slice"] for t in tops} == {"ALL", "BULL"}
    assert len({t["slice_comparison_key"] for t in tops}) == 2
