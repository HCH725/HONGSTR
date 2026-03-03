import json
from pathlib import Path

from research.loop.dca_cost_model import estimate_cost_breakdown

FIX = Path("/Users/hong/Projects/HONGSTR/research/loop/tests/fixtures/dca")


def test_l3_fixed_bps_when_no_orderbook_and_no_market_stats():
    out = estimate_cost_breakdown(order_notional=1000.0, orderbook=None, market_stats=None)
    assert out["slippage_source"] == "L3_FIXED_BPS"
    assert out["slippage_bps"] == 9.0
    assert out["total_cost_bps"] == 14.0
    assert out["fee_scenario"] == "standard"


def test_l2_spread_vol_deterministic_output():
    out = estimate_cost_breakdown(
        order_notional=1000.0,
        orderbook=None,
        market_stats={"spread_bps": 8.0, "realized_vol_pct": 1.2},
    )
    assert out["slippage_source"] == "L2_SPREAD_VOL"
    assert out["slippage_bps"] == 47.2
    assert out["total_cost_bps"] == 52.2


def test_orderbook_missing_fields_fallback_to_l3_fixture():
    payload = json.loads((FIX / "orderbook_missing.json").read_text(encoding="utf-8"))
    out = estimate_cost_breakdown(
        order_notional=payload["order_notional"],
        orderbook=payload["orderbook"],
        market_stats=payload["market_stats"],
    )
    assert out["slippage_source"] == payload["expected"]["slippage_source"]
    assert out["fallback_reason"] in {"orderbook_ts_missing", "orderbook_unusable"}


def test_lookahead_orderbook_downgrades_to_l2():
    out = estimate_cost_breakdown(
        order_notional=1200.0,
        orderbook={
            "bid_px": 100.0,
            "ask_px": 100.3,
            "bid_size": 6.0,
            "ask_size": 6.0,
            "signal_ts": "2026-02-26T10:00:00Z",
            "snapshot_ts": "2026-02-26T10:00:01Z",
        },
        market_stats={"spread_bps": 5.0, "realized_vol_pct": 1.0},
    )
    assert out["slippage_source"] == "L2_SPREAD_VOL"
    assert out["lookahead_safe"] is False
    assert "lookahead" in out["fallback_reason"]


def test_fee_scenarios_standard_vip_stress():
    std = estimate_cost_breakdown(order_notional=500.0, orderbook=None, market_stats=None, fee_scenario="standard")
    vip = estimate_cost_breakdown(order_notional=500.0, orderbook=None, market_stats=None, fee_scenario="vip")
    stress = estimate_cost_breakdown(order_notional=500.0, orderbook=None, market_stats=None, fee_scenario="stress")

    assert vip["fee_bps"] < std["fee_bps"] < stress["fee_bps"]
    assert stress["fee_bps"] == std["fee_bps"] * 2
