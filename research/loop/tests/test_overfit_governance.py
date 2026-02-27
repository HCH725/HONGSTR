import json
from pathlib import Path

from research.loop.gates import ResearchGate


def test_gate_policy_hard_and_soft_tiers(tmp_path: Path):
    policy = {
        "name": "test_policy",
        "hard_gates": {
            "min_oos_sharpe": 0.8,
            "max_oos_mdd": -0.15,
            "min_trades_count": 20,
            "min_pnl_mult": 1.02,
            "max_is_oos_sharpe_ratio": 2.5,
        },
        "soft_targets": {
            "oos_sharpe": 1.0,
            "oos_mdd": -0.10,
            "trades_count": 40,
            "pnl_mult": 1.06,
        },
        "soft_penalties": {
            "oos_sharpe_below_target": 10.0,
            "oos_mdd_worse_target": 8.0,
            "trades_shortfall": 6.0,
            "pnl_shortfall": 8.0,
        },
        "score": {"base": 100.0, "clip_min": 0.0, "clip_max": 160.0, "hard_fail_penalty": 30.0},
        "watchlist": {"min_candidates": 1, "recommend_if_score_ge": 50.0},
    }
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(json.dumps(policy), encoding="utf-8")

    gate = ResearchGate(policy_path=policy_path)
    out = gate.evaluate_detailed(
        {
            "status": "SUCCESS",
            "is_sharpe": 2.2,
            "oos_sharpe": 0.6,
            "oos_mdd": -0.25,
            "trades_count": 8,
            "pnl_mult": 0.96,
        }
    )
    as_dict = out.as_dict()
    assert out.passed is False
    assert as_dict["policy_name"] == "test_policy"
    assert len(as_dict["hard_failures"]) >= 3
    assert as_dict["final_score"] < 100
    assert as_dict["recommendation"] in {"WATCHLIST", "DEMOTE"}


def test_watchlist_floor_prevents_empty_candidates():
    gate = ResearchGate()
    ranked = [
        {"id": "A", "final_score": 40.0, "recommendation": "DEMOTE"},
        {"id": "B", "final_score": 35.0, "recommendation": "DEMOTE"},
    ]
    out = gate.apply_watchlist_floor(ranked)
    assert out
    assert any(str(x.get("recommendation", "")).upper() == "WATCHLIST" for x in out)
