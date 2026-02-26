import json

from research.loop.dca1_executor import (
    Dca1ExecutorConfig,
    DcaCostModelConfig,
    generate_dca1_artifacts,
    run_dca1_backtest_report_only,
)


def test_dca1_backtest_report_only_basic():
    cfg = Dca1ExecutorConfig(
        base_order_qty=1.0,
        safety_multiplier=1.5,
        safety_spacing_pct=0.02,
        take_profit_pct=0.03,
        stop_loss_pct=0.05,
        trailing_pct=None,
        cost_model=DcaCostModelConfig(fee_bps=4.0, fixed_slippage_bps=8.0),
    )
    prices = [100.0, 98.5, 97.9, 100.2, 103.5]
    out = run_dca1_backtest_report_only(prices=prices, config=cfg)
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["orders_count"] >= 2
    assert "cost_breakdown" in out
    assert set(out["cost_breakdown"].keys()) >= {
        "fee_bps",
        "slippage_bps",
        "total_cost_bps",
        "slippage_source",
    }


def test_dca1_generate_artifacts_shape(tmp_path):
    out_dir = tmp_path / "reports" / "research" / "20260201" / "EXP_DCA1"
    artifacts = generate_dca1_artifacts(
        out_dir=out_dir,
        strategy_id="dca1_cost_aware_v1",
        symbol="BTCUSDT",
        timeframe="1h",
        prices=[100.0, 98.3, 99.1, 101.4, 103.2],
    )

    assert (out_dir / "summary.json").exists()
    assert (out_dir / "selection.json").exists()
    assert (out_dir / "gate.json").exists()
    assert (out_dir / "report.md").exists()
    assert (out_dir / "dca1_cost_aware_v1_results.json").exists()

    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    gate = json.loads((out_dir / "gate.json").read_text(encoding="utf-8"))
    selection = json.loads((out_dir / "selection.json").read_text(encoding="utf-8"))

    assert summary["report_only"] is True
    assert summary["actions"] == []
    assert "cost_breakdown" in summary
    assert gate["results"]["overall"]["portfolio_trades"] >= 2
    assert selection["decision"] in {"TRADE", "HOLD"}
    assert artifacts["results"]["report_only"] is True
