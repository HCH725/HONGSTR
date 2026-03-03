from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

DEFAULT_COST_CONFIG: dict[str, float] = {
    "l3_fixed_slippage_bps": 9.0,
    "l2_spread_weight": 0.65,
    "l2_vol_weight": 0.35,
    "l2_vol_to_bps": 100.0,
    "l1_impact_weight": 0.8,
    "max_lookahead_ms": 0.0,
}

DEFAULT_FEE_BPS_BY_SCENARIO: dict[str, float] = {
    "standard": 5.0,
    "vip": 3.0,
    "stress": 10.0,
}


@dataclass(frozen=True)
class CostBreakdown:
    fee_bps: float
    slippage_bps: float
    total_cost_bps: float
    slippage_source: str
    fee_scenario: str
    lookahead_safe: bool
    fallback_reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "fee_bps": round(self.fee_bps, 6),
            "slippage_bps": round(self.slippage_bps, 6),
            "total_cost_bps": round(self.total_cost_bps, 6),
            "slippage_source": self.slippage_source,
            "fee_scenario": self.fee_scenario,
            "lookahead_safe": self.lookahead_safe,
            "fallback_reason": self.fallback_reason,
        }


def estimate_cost_breakdown(
    *,
    order_notional: float,
    orderbook: dict[str, Any] | None = None,
    market_stats: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    fee_scenario: str = "standard",
    fee_bps_override: float | None = None,
) -> dict[str, Any]:
    cfg = dict(DEFAULT_COST_CONFIG)
    if isinstance(config, dict):
        for k, v in config.items():
            try:
                cfg[k] = float(v)
            except Exception:
                continue

    fee_by_scenario = dict(DEFAULT_FEE_BPS_BY_SCENARIO)
    if isinstance(config, dict):
        custom = config.get("fee_bps_by_scenario")
        if isinstance(custom, dict):
            for k, v in custom.items():
                try:
                    fee_by_scenario[str(k)] = float(v)
                except Exception:
                    continue

    scenario = str(fee_scenario or "standard").strip().lower()
    if scenario not in fee_by_scenario:
        scenario = "standard"

    fee_bps = _safe_float(fee_bps_override, fee_by_scenario[scenario])

    if orderbook:
        lookahead_safe, lookahead_reason = _orderbook_timestamp_safe(
            orderbook,
            max_lookahead_ms=_safe_float(cfg.get("max_lookahead_ms"), 0.0),
        )
        if lookahead_safe:
            l1 = _estimate_l1_slippage(order_notional=order_notional, orderbook=orderbook, cfg=cfg)
            if l1 is not None:
                return CostBreakdown(
                    fee_bps=fee_bps,
                    slippage_bps=l1,
                    total_cost_bps=fee_bps + l1,
                    slippage_source="L1_ORDERBOOK_IMPACT",
                    fee_scenario=scenario,
                    lookahead_safe=True,
                    fallback_reason="",
                ).as_dict()
            lookahead_reason = "orderbook_unusable"

        l2 = _estimate_l2_slippage(market_stats=market_stats, cfg=cfg)
        if l2 is not None:
            return CostBreakdown(
                fee_bps=fee_bps,
                slippage_bps=l2,
                total_cost_bps=fee_bps + l2,
                slippage_source="L2_SPREAD_VOL",
                fee_scenario=scenario,
                lookahead_safe=False,
                fallback_reason=lookahead_reason,
            ).as_dict()

        l3 = _safe_float(cfg.get("l3_fixed_slippage_bps"), 9.0)
        return CostBreakdown(
            fee_bps=fee_bps,
            slippage_bps=l3,
            total_cost_bps=fee_bps + l3,
            slippage_source="L3_FIXED_BPS",
            fee_scenario=scenario,
            lookahead_safe=False,
            fallback_reason=lookahead_reason,
        ).as_dict()

    l2 = _estimate_l2_slippage(market_stats=market_stats, cfg=cfg)
    if l2 is not None:
        return CostBreakdown(
            fee_bps=fee_bps,
            slippage_bps=l2,
            total_cost_bps=fee_bps + l2,
            slippage_source="L2_SPREAD_VOL",
            fee_scenario=scenario,
            lookahead_safe=False,
            fallback_reason="orderbook_missing",
        ).as_dict()

    l3 = _safe_float(cfg.get("l3_fixed_slippage_bps"), 9.0)
    return CostBreakdown(
        fee_bps=fee_bps,
        slippage_bps=l3,
        total_cost_bps=fee_bps + l3,
        slippage_source="L3_FIXED_BPS",
        fee_scenario=scenario,
        lookahead_safe=False,
        fallback_reason="orderbook_missing",
    ).as_dict()


def _estimate_l1_slippage(*, order_notional: float, orderbook: dict[str, Any], cfg: dict[str, float]) -> float | None:
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

    slippage = (spread_bps * 0.5) + (spread_bps * impact_ratio * impact_weight)
    return round(max(0.0, slippage), 6)


def _estimate_l2_slippage(*, market_stats: dict[str, Any] | None, cfg: dict[str, float]) -> float | None:
    if not isinstance(market_stats, dict):
        return None

    spread_bps = _safe_float(market_stats.get("spread_bps"), None)
    vol_pct = _safe_float(market_stats.get("realized_vol_pct", market_stats.get("vol_pct")), None)
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

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        out = datetime.fromisoformat(text)
    except Exception:
        return None

    if out.tzinfo is None:
        out = out.replace(tzinfo=timezone.utc)
    return out.astimezone(timezone.utc)


def _safe_float(value: Any, default: float | None = 0.0) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except Exception:
        return default
