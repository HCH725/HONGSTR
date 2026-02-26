import json
from pathlib import Path

from research.loop.dca_cost_model import DcaCostModelConfig, estimate_trade_cost_bps

FIX_DIR = Path(__file__).resolve().parent / "fixtures" / "dca_cost"


def test_l3_fixed_fallback_deterministic():
    cfg = DcaCostModelConfig(fee_bps=4.0, fixed_slippage_bps=8.0)
    out = estimate_trade_cost_bps(
        order_qty=1.0,
        side="BUY",
        order_ts="2026-02-01T00:00:00Z",
        market_ctx={},
        config=cfg,
    )
    assert out["slippage_source"] == "L3_FIXED_BPS"
    assert out["fee_bps"] == 4.0
    assert out["slippage_bps"] == 8.0
    assert out["total_cost_bps"] == 12.0


def test_l2_spread_vol_deterministic():
    cfg = DcaCostModelConfig(
        fee_bps=3.0,
        fixed_slippage_bps=9.0,
        l2_vol_weight=0.20,
        l2_size_weight_bps_per_unit=0.10,
    )
    out = estimate_trade_cost_bps(
        order_qty=2.0,
        side="BUY",
        order_ts="2026-02-01T00:00:00Z",
        market_ctx={
            "bbo": {"bid": 99.9, "ask": 100.1},
            "volatility_bps": 30.0,
        },
        config=cfg,
    )
    # spread_bps ~= 20.0 => 10.0 half-spread + 6.0 vol + 0.2 size = 16.2
    assert out["slippage_source"] == "L2_SPREAD_VOL"
    assert out["slippage_bps"] == 16.2
    assert out["total_cost_bps"] == 19.2


def test_orderbook_missing_fixture_fallback_to_l3():
    payload = json.loads((FIX_DIR / "orderbook_missing.json").read_text(encoding="utf-8"))
    cfg = DcaCostModelConfig(fee_bps=5.0, fixed_slippage_bps=7.5)
    out = estimate_trade_cost_bps(
        order_qty=float(payload["order_qty"]),
        side=str(payload["side"]),
        order_ts=str(payload["order_ts"]),
        market_ctx=dict(payload["market_ctx"]),
        config=cfg,
    )
    assert out["slippage_source"] == "L3_FIXED_BPS"
    assert out["slippage_bps"] == 7.5
    assert out["total_cost_bps"] == 12.5


def test_orderbook_lookahead_guard_downgrades_to_l2():
    cfg = DcaCostModelConfig(
        fee_bps=4.0,
        fixed_slippage_bps=8.0,
        l2_vol_weight=0.10,
        l2_size_weight_bps_per_unit=0.05,
        max_lookahead_ms=0,
    )
    out = estimate_trade_cost_bps(
        order_qty=1.0,
        side="BUY",
        order_ts="2026-02-01T00:00:00Z",
        market_ctx={
            "orderbook_snapshots": [
                {
                    "ts": "2026-02-01T00:00:00.500000Z",
                    "bids": [[99.95, 5.0]],
                    "asks": [[100.05, 5.0]],
                }
            ],
            "bbo": {"bid": 99.9, "ask": 100.1},
            "volatility_bps": 20.0,
        },
        config=cfg,
    )
    assert out["lookahead_audit"]["status"] == "FAIL"
    assert out["slippage_source"] == "L2_SPREAD_VOL"
