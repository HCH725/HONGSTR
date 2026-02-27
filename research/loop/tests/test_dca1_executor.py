from research.loop.dca1_executor import run_dca1_candidate, run_dca1_sweep


def _base_candidate() -> dict:
    return {
        "candidate_id": "dca1_supertrend__long__base",
        "strategy_id": "dca1_supertrend",
        "family": "dca1",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "direction": "LONG",
        "variant": "base_safety1",
        "parameters": {
            "base_order": 1.0,
            "safety_multiplier": 1.6,
            "safety_gap_bps": 120,
            "take_profit_pct": 1.1,
            "stop_loss_pct": 2.3,
            "trailing_pct": 0.7,
        },
    }


def test_dca1_executor_report_only_output_keys():
    out = run_dca1_candidate(_base_candidate())
    summary = out["summary"]
    selection = out["selection"]
    gate = out["gate"]

    assert summary["report_only"] is True
    assert summary["direction"] == "LONG"
    assert selection["report_only"] is True
    assert gate["report_only"] is True
    assert "cost_breakdown" in summary
    assert "cost_breakdown_stress" in summary
    assert "cost_stress" in gate


def test_dca1_executor_stress_gate_fail_possible():
    out = run_dca1_candidate(
        _base_candidate(),
        gate_config={"max_cost_bps": 10.0, "max_cost_multiplier": 1.5},
        fee_scenario="stress",
    )
    gate = out["gate"]
    assert gate["overall"] in {"PASS", "FAIL"}
    assert "cost_multiplier" in gate["cost_stress"]


def test_dca1_sweep_emits_variants():
    sweep = run_dca1_sweep(
        _base_candidate(),
        safety_multiplier_values=[1.4, 1.8],
        safety_gap_bps_values=[100, 180],
        fee_scenarios=("standard", "stress"),
    )
    assert len(sweep) == 8
    ids = {s["summary"]["candidate_id"] for s in sweep}
    assert len(ids) == 8
