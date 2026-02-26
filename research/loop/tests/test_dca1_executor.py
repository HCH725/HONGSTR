from research.loop.dca1_executor import run_dca1_candidate


def test_dca1_executor_report_only_output_keys():
    candidate = {
        "candidate_id": "dca1_supertrend__long__base",
        "strategy_id": "dca1_supertrend",
        "family": "dca1",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "direction": "LONG",
        "variant": "base_safety1",
        "parameters": {
            "base_order": 1.0,
            "safety_mult": 1.6,
            "spacing_pct": 1.2,
            "take_profit_pct": 1.1,
            "stop_loss_pct": 2.3,
            "trailing_pct": 0.7,
        },
    }

    out = run_dca1_candidate(candidate)
    summary = out["summary"]
    selection = out["selection"]
    metrics = out["metrics"]

    assert summary["report_only"] is True
    assert summary["direction"] == "LONG"
    assert selection["report_only"] is True
    assert selection["candidate_id"] == candidate["candidate_id"]
    assert "cost_breakdown" in summary
    assert metrics["candidate_id"] == candidate["candidate_id"]


def test_dca1_executor_dry_run():
    candidate = {
        "candidate_id": "dca1_supertrend__short__base",
        "strategy_id": "dca1_supertrend",
        "family": "dca1",
        "direction": "SHORT",
        "parameters": {},
    }
    out = run_dca1_candidate(candidate, dry_run=True)
    assert out["summary"]["status"] == "DRY_RUN"
    assert out["metrics"]["status"] == "DRY_RUN"
    assert out["selection"]["decision"] == "DRY_RUN"
