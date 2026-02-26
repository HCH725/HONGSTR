from research.loop.gates import ResearchGate


def test_gate_pass_with_aggressive_policy():
    gate = ResearchGate()
    result = gate.evaluate_detailed(
        {
            "status": "SUCCESS",
            "is_sharpe": 1.4,
            "oos_sharpe": 1.0,
            "is_mdd": -0.10,
            "oos_mdd": -0.12,
            "trades_count": 40,
            "pnl_mult": 1.10,
            "total_cost_bps": 12.0,
        }
    )
    assert result.passed is True
    as_dict = result.as_dict()
    assert as_dict["policy_name"]
    assert as_dict["final_score"] > 90.0


def test_gate_fail_on_hard_rules():
    gate = ResearchGate()
    result = gate.evaluate_detailed(
        {
            "status": "SUCCESS",
            "is_sharpe": 2.0,
            "oos_sharpe": 0.2,
            "is_mdd": -0.25,
            "oos_mdd": -0.30,
            "trades_count": 4,
            "pnl_mult": 0.92,
            "total_cost_bps": 30.0,
        }
    )
    assert result.passed is False
    as_dict = result.as_dict()
    assert as_dict["hard_failures"]
    assert as_dict["final_score"] <= 180.0
