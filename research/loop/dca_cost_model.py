from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_COST_CONFIG: dict[str, float] = {
    "fee_bps": 5.0,
    "l3_fixed_slippage_bps": 9.0,
    "l2_spread_weight": 0.65,
    "l2_vol_weight": 0.35,
    "l2_vol_to_bps": 100.0,
    "l1_impact_weight": 0.8,
    "max_lookahead_ms": 0.0,
}


@dataclass(frozen=True)
class CostBreakdown:
    fee_bps: float
    slippage_bps: float
    total_cost_bps: float
    slippage_source: str
    lookahead_safe: bool
    fallback_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "fee_bps": round(self.fee_bps, 6),
            "slippage_bps": round(self.slippage_bps, 6),
            "total_cost_bps": round(self.total_cost_bps, 6),
            "slippage_source": self.slippage_source,
            "lookahead_safe": self.lookahead_safe,
            "fallback_reason": self.fallback_reason,
        }


def estimate_cost_breakdown(
    *,
    order_notional: float,
    fee_bps: float | None = None,
    orderbook: dict[str, Any] | None = None,
    market_stats: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = dict(DEFAULT_COST_CONFIG)
    if isinstance(config, dict):
        for k, v in config.items():
            try:
                cfg[k] = float(v)
            except Exception:
                continue

    fee = _safe_float(fee_bps, cfg["fee_bps"])

    if orderbook:
        lookahead_safe, lookahead_reason = _orderbook_timestamp_safe(
            orderbook,
            max_lookahead_ms=_safe_float(cfg.get("max_lookahead_ms"), 0.0),
        )
        if lookahead_safe:
            slippage = _estimate_l1_slippage(order_notional=order_notional, orderbook=orderbook, cfg=cfg)
            if slippage is not None:
                result = CostBreakdown(
                    fee_bps=fee,
                    slippage_bps=slippage,
                    total_cost_bps=fee + slippage,
                    slippage_source="L1_ORDERBOOK_IMPACT",
                    lookahead_safe=True,
                    fallback_reason="",
                )
                return result.as_dict()
            lookahead_reason = "orderbook_unusable"

        # timestamp check failed or L1 unusable -> L2/L3 fallback
        l2 = _estimate_l2_slippage(market_stats=market_stats, cfg=cfg)
        if l2 is not None:
            result = CostBreakdown(
                fee_bps=fee,
                slippage_bps=l2,
                total_cost_bps=fee + l2,
                slippage_source="L2_SPREAD_VOL",
                lookahead_safe=False,
                fallback_reason=lookahead_reason,
            )
            return result.as_dict()

        l3 = _safe_float(cfg.get("l3_fixed_slippage_bps"), 9.0)
        result = CostBreakdown(
            fee_bps=fee,
            slippage_bps=l3,
            total_cost_bps=fee + l3,
            slippage_source="L3_FIXED_BPS",
            lookahead_safe=False,
            fallback_reason=lookahead_reason,
        )
        return result.as_dict()

    # No orderbook: L2 then L3
    l2 = _estimate_l2_slippage(market_stats=market_stats, cfg=cfg)
    if l2 is not None:
        result = CostBreakdown(
            fee_bps=fee,
            slippage_bps=l2,
            total_cost_bps=fee + l2,
            slippage_source="L2_SPREAD_VOL",
            lookahead_safe=False,
            fallback_reason="orderbook_missing",
        )
        return result.as_dict()

    l3 = _safe_float(cfg.get("l3_fixed_slippage_bps"), 9.0)
    result = CostBreakdown(
        fee_bps=fee,
        slippage_bps=l3,
        total_cost_bps=fee + l3,
        slippage_source="L3_FIXED_BPS",
        lookahead_safe=False,
        fallback_reason="orderbook_missing",
    )
    return result.as_dict()


def _estimate_l1_slippage(
    *,
    order_notional: float,
    orderbook: dict[str, Any],
    cfg: dict[str, float],
) -> float | None:
    bid = _safe_float(orderbook.get("bid_px"), None)
    ask = _safe_float(orderbook.get("ask_px"), None)
    bid_sz = _safe_float(orderbook.get("bid_size"), None)
    ask_sz = _safe_float(orderbook.get("ask_size"), None)

    if bid is None or ask is None or bid_sz is None or ask_sz is None:
        return None
    if bid <= 0 or ask <= 0 or ask <= bid:
        return None
    if bid_sz <= 0 or ask_sz <= 0:
        return None

    mid = (bid + ask) / 2.0
    spread_bps = ((ask - bid) / mid) * 10000.0

    depth_notional = ((bid_sz + ask_sz) / 2.0) * mid
    impact_ratio = max(0.0, min(5.0, order_notional / max(depth_notional, 1e-9)))
    impact_weight = _safe_float(cfg.get("l1_impact_weight"), 0.8)

    # Half-spread crossing + depth impact penalty.
    slippage = (spread_bps * 0.5) + (spread_bps * impact_ratio * impact_weight)
    return round(max(0.0, slippage), 6)


def _estimate_l2_slippage(
    *,
    market_stats: dict[str, Any] | None,
    cfg: dict[str, float],
) -> float | None:
    if not isinstance(market_stats, dict):
        return None

    spread_bps = _safe_float(market_stats.get("spread_bps"), None)
    vol_pct = _safe_float(
        market_stats.get("realized_vol_pct", market_stats.get("vol_pct")),
        None,
    )
    if spread_bps is None or vol_pct is None:
        return None

    spread_w = _safe_float(cfg.get("l2_spread_weight"), 0.65)
    vol_w = _safe_float(cfg.get("l2_vol_weight"), 0.35)
    vol_to_bps = _safe_float(cfg.get("l2_vol_to_bps"), 100.0)

    slippage = (spread_bps * spread_w) + (vol_pct * vol_to_bps * vol_w)
    return round(max(0.0, slippage), 6)


def _orderbook_timestamp_safe(orderbook: dict[str, Any], max_lookahead_ms: float) -> tuple[bool, str]:
    snap_ts = _parse_ts(orderbook.get("snapshot_ts") or orderbook.get("ts"))
    signal_ts = _parse_ts(orderbook.get("signal_ts"))

    if snap_ts is None or signal_ts is None:
        return False, "orderbook_ts_missing"

    skew_ms = (snap_ts - signal_ts).total_seconds() * 1000.0
    if skew_ms > max_lookahead_ms:
        return False, f"orderbook_lookahead_ms={skew_ms:.1f}"
    return True, ""


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    txt = str(value).strip()
    if not txt:
        return None

    if txt.endswith("Z"):
        txt = txt[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(txt)
    except Exception:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default
