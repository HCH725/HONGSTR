from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import pandas as pd

from research.audit.lookahead import SignalLeakageAudit


@dataclass
class DcaCostModelConfig:
    fee_bps: float = 4.0
    fixed_slippage_bps: float = 8.0
    l2_vol_weight: float = 0.15
    l2_size_weight_bps_per_unit: float = 0.02
    l1_depth_shortfall_penalty_bps: float = 5.0
    max_lookahead_ms: int = 0


def _parse_ts(ts_value: object) -> datetime | None:
    if ts_value is None:
        return None
    try:
        return pd.to_datetime(ts_value, utc=True).to_pydatetime()
    except Exception:
        return None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_level(level: object) -> tuple[float, float] | None:
    if isinstance(level, dict):
        price = level.get("price")
        size = level.get("size")
    elif isinstance(level, (list, tuple)) and len(level) >= 2:
        price = level[0]
        size = level[1]
    else:
        return None
    try:
        p = float(price)
        s = float(size)
        if p <= 0.0 or s <= 0.0:
            return None
        return p, s
    except Exception:
        return None


def _iter_levels(levels: Iterable[object]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for lv in levels:
        parsed = _normalize_level(lv)
        if parsed is not None:
            out.append(parsed)
    return out


def _mid_from_snapshot(snapshot: dict[str, Any]) -> float | None:
    bids = _iter_levels(snapshot.get("bids", []))
    asks = _iter_levels(snapshot.get("asks", []))
    if not bids or not asks:
        return None
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    if best_ask <= 0 or best_bid <= 0:
        return None
    return (best_bid + best_ask) / 2.0


def _pick_snapshot(order_ts: str, market_ctx: dict[str, Any]) -> dict[str, Any] | None:
    snapshots = market_ctx.get("orderbook_snapshots")
    if isinstance(snapshots, dict):
        snapshots = [snapshots]
    if not isinstance(snapshots, list) or not snapshots:
        return None

    target = _parse_ts(order_ts)
    if target is None:
        for item in snapshots:
            if isinstance(item, dict):
                return item
        return None

    best: dict[str, Any] | None = None
    best_ts: datetime | None = None
    future_best: dict[str, Any] | None = None
    future_ts: datetime | None = None
    for item in snapshots:
        if not isinstance(item, dict):
            continue
        ts = _parse_ts(item.get("ts"))
        if ts is None:
            continue
        if ts <= target and (best_ts is None or ts > best_ts):
            best = item
            best_ts = ts
        elif ts > target and (future_ts is None or ts < future_ts):
            future_best = item
            future_ts = ts
    # Use nearest future snapshot when no on-time snapshot exists;
    # lookahead guard will downgrade it if timestamp is unsafe.
    return best or future_best


def _audit_orderbook_timestamp(order_ts: str, snapshot_ts: str, max_lookahead_ms: int) -> dict[str, Any]:
    panel = pd.DataFrame(
        [
            {"ts": order_ts, "symbol": "OB", "close": 1.0},
            {"ts": order_ts, "symbol": "OB", "close": 1.0},
        ]
    )
    features = pd.DataFrame(
        [
            {"ts": order_ts, "symbol": "OB", "ob_signal": 0.1, "source_ts": snapshot_ts},
            {"ts": order_ts, "symbol": "OB", "ob_signal": 0.2, "source_ts": snapshot_ts},
        ]
    )
    labels = pd.DataFrame(
        [
            {"ts": order_ts, "symbol": "OB", "direction": 0.0},
            {"ts": order_ts, "symbol": "OB", "direction": 1.0},
        ]
    )
    audit = SignalLeakageAudit(max_allowed_lookahead_ms=max_lookahead_ms)
    return audit.audit(panel=panel, features=features, labels=labels)


def _l1_orderbook_impact_slippage_bps(
    side: str,
    order_qty: float,
    snapshot: dict[str, Any],
    config: DcaCostModelConfig,
) -> tuple[float, dict[str, Any]]:
    bids = _iter_levels(snapshot.get("bids", []))
    asks = _iter_levels(snapshot.get("asks", []))
    mid = _mid_from_snapshot(snapshot)
    if mid is None:
        raise ValueError("orderbook snapshot missing bids/asks")

    book_side = asks if side.upper() == "BUY" else bids
    if not book_side:
        raise ValueError("orderbook side empty")

    remain = float(order_qty)
    fill_notional = 0.0
    filled = 0.0
    for price, size in book_side:
        if remain <= 0:
            break
        take = min(remain, size)
        fill_notional += take * price
        filled += take
        remain -= take

    if filled <= 0:
        raise ValueError("no fill from orderbook depth")

    avg_fill = fill_notional / filled
    raw_slippage = abs(avg_fill - mid) / mid * 10000.0
    shortfall_penalty = 0.0
    if remain > 1e-12:
        shortfall_penalty = config.l1_depth_shortfall_penalty_bps
    slippage = raw_slippage + shortfall_penalty
    details = {
        "mid_price": mid,
        "avg_fill_price": avg_fill,
        "filled_qty": filled,
        "remaining_qty": max(0.0, remain),
        "raw_slippage_bps": raw_slippage,
        "shortfall_penalty_bps": shortfall_penalty,
    }
    return slippage, details


def _l2_slippage_bps(order_qty: float, market_ctx: dict[str, Any], config: DcaCostModelConfig) -> tuple[float, dict[str, Any]]:
    spread_bps = market_ctx.get("spread_bps")
    try:
        spread_bps = float(spread_bps)
    except Exception:
        spread_bps = None

    if spread_bps is None or spread_bps <= 0:
        bbo = market_ctx.get("bbo")
        if isinstance(bbo, dict):
            try:
                bid = float(bbo.get("bid"))
                ask = float(bbo.get("ask"))
                mid = (bid + ask) / 2.0
                if bid > 0 and ask > 0 and mid > 0:
                    spread_bps = (ask - bid) / mid * 10000.0
            except Exception:
                spread_bps = None

    if spread_bps is None or spread_bps <= 0:
        raise ValueError("L2 needs spread/bbo data")

    vol_bps = market_ctx.get("volatility_bps", market_ctx.get("vol_bps", 0.0))
    try:
        vol_bps = max(0.0, float(vol_bps))
    except Exception:
        vol_bps = 0.0

    size_penalty = abs(float(order_qty)) * config.l2_size_weight_bps_per_unit
    slippage = (spread_bps * 0.5) + (vol_bps * config.l2_vol_weight) + size_penalty
    details = {
        "spread_bps": spread_bps,
        "volatility_bps": vol_bps,
        "size_penalty_bps": size_penalty,
    }
    return slippage, details


def estimate_trade_cost_bps(
    *,
    order_qty: float,
    side: str,
    order_ts: str,
    market_ctx: dict[str, Any] | None = None,
    config: DcaCostModelConfig | None = None,
) -> dict[str, Any]:
    cfg = config or DcaCostModelConfig()
    ctx = market_ctx or {}
    fee_bps = float(cfg.fee_bps)
    slippage_bps = float(cfg.fixed_slippage_bps)
    slippage_source = "L3_FIXED_BPS"
    details: dict[str, Any] = {"fallback_reason": "fixed_default"}
    audit_payload: dict[str, Any] = {}

    snapshot = _pick_snapshot(order_ts, ctx)
    if isinstance(snapshot, dict):
        snapshot_ts = str(snapshot.get("ts") or "")
        audit_payload = _audit_orderbook_timestamp(order_ts, snapshot_ts, cfg.max_lookahead_ms)
        if str(audit_payload.get("status", "UNKNOWN")).upper() == "OK":
            try:
                l1_slippage, l1_details = _l1_orderbook_impact_slippage_bps(
                    side=side, order_qty=order_qty, snapshot=snapshot, config=cfg
                )
                slippage_bps = l1_slippage
                slippage_source = "L1_ORDERBOOK_IMPACT"
                details = l1_details
            except Exception as exc:
                details = {"fallback_reason": f"l1_error:{type(exc).__name__}"}
        else:
            details = {
                "fallback_reason": "lookahead_guard_fail",
                "audit_status": audit_payload.get("status"),
            }

    if slippage_source == "L3_FIXED_BPS":
        try:
            l2_slippage, l2_details = _l2_slippage_bps(order_qty=order_qty, market_ctx=ctx, config=cfg)
            slippage_bps = l2_slippage
            slippage_source = "L2_SPREAD_VOL"
            details = l2_details
        except Exception:
            if "fallback_reason" not in details:
                details = {"fallback_reason": "l2_unavailable"}

    total_cost_bps = fee_bps + slippage_bps
    return {
        "timestamp": _utc_now_iso(),
        "fee_bps": round(fee_bps, 6),
        "slippage_bps": round(float(slippage_bps), 6),
        "total_cost_bps": round(float(total_cost_bps), 6),
        "slippage_source": slippage_source,
        "slippage_details": details,
        "lookahead_audit": audit_payload,
    }
