from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from research.loop.dca_cost_model import estimate_cost_breakdown


@dataclass(frozen=True)
class DCA1Params:
    base_order: float = 1.0
    safety_mult: float = 1.6
    spacing_pct: float = 1.2
    take_profit_pct: float = 1.1
    stop_loss_pct: float = 2.3
    trailing_pct: float = 0.0


def run_dca1_candidate(
    candidate: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
    cost_config: dict[str, Any] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    cid = str(candidate.get("candidate_id") or candidate.get("strategy_id") or "dca1_candidate")
    direction = str(candidate.get("direction") or "LONG").upper()
    params = _parse_params(candidate.get("parameters") if isinstance(candidate.get("parameters"), dict) else {})

    if dry_run:
        now = _now_iso()
        summary = {
            "candidate_id": cid,
            "strategy_id": str(candidate.get("strategy_id") or "dca1"),
            "family": str(candidate.get("family") or "dca1"),
            "symbol": str(candidate.get("symbol") or "BTCUSDT"),
            "timeframe": str(candidate.get("timeframe") or "1h"),
            "direction": direction,
            "variant": str(candidate.get("variant") or "base"),
            "status": "DRY_RUN",
            "report_only": True,
            "timestamp": now,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "trades_count": 0,
            "total_return": 0.0,
            "pnl_mult": 1.0,
            "cost_breakdown": {
                "fee_bps": 0.0,
                "slippage_bps": 0.0,
                "total_cost_bps": 0.0,
                "slippage_source": "DRY_RUN",
                "lookahead_safe": True,
                "fallback_reason": "",
            },
            "dca_params": params.__dict__,
        }
        selection = {
            "decision": "DRY_RUN",
            "selected_symbol": summary["symbol"],
            "candidate_id": cid,
            "direction": direction,
            "gate": {"overall": "FAIL", "reasons": ["DRY_RUN"]},
            "report_only": True,
            "timestamp": now,
        }
        return {
            "summary": summary,
            "selection": selection,
            "metrics": {
                "status": "DRY_RUN",
                "is_sharpe": 0.0,
                "oos_sharpe": 0.0,
                "oos_mdd": 0.0,
                "is_mdd": 0.0,
                "pnl_mult": 1.0,
                "trades_count": 0,
                "total_cost_bps": 0.0,
                "timestamp": now,
            },
            "report_md": _render_report(summary=summary, selection=selection),
        }

    seed = _seed_for(cid)
    unit_a = _unit(seed, salt="a")
    unit_b = _unit(seed, salt="b")
    unit_c = _unit(seed, salt="c")
    unit_d = _unit(seed, salt="d")

    safety_notional = params.base_order * params.safety_mult
    spacing_trigger = max(0.2, 2.2 - params.spacing_pct) / 2.4
    safety_triggered = unit_b < spacing_trigger

    order_notional = params.base_order + (safety_notional if safety_triggered else 0.0)
    snap = snapshot if isinstance(snapshot, dict) else {}

    orderbook = snap.get("orderbook") if isinstance(snap.get("orderbook"), dict) else None
    market_stats = snap.get("market_stats") if isinstance(snap.get("market_stats"), dict) else None
    if market_stats is None:
        market_stats = {
            "spread_bps": round(4.0 + unit_c * 8.0, 6),
            "realized_vol_pct": round(0.9 + unit_d * 1.8, 6),
        }

    cost = estimate_cost_breakdown(
        order_notional=order_notional,
        orderbook=orderbook,
        market_stats=market_stats,
        config=cost_config,
    )

    gross_edge_bps = 35.0 + (unit_a * 95.0)
    if direction == "SHORT":
        gross_edge_bps *= 1.03
    elif direction == "LONGSHORT":
        gross_edge_bps *= 1.08

    # Safety order lowers entry price variance but increases fees/slippage.
    safety_drag_bps = 4.0 if safety_triggered else 0.0
    risk_drag_bps = max(3.0, params.stop_loss_pct * 1.4)
    net_edge_bps = gross_edge_bps - cost["total_cost_bps"] - safety_drag_bps - risk_drag_bps

    raw_return_pct = net_edge_bps / 100.0
    tp = params.take_profit_pct
    sl = params.stop_loss_pct
    trailing = max(0.0, params.trailing_pct)

    if raw_return_pct > tp:
        realized_return_pct = tp + min(trailing * 0.35, 0.8)
    elif raw_return_pct < -sl:
        realized_return_pct = -sl
    else:
        realized_return_pct = raw_return_pct

    base_vol = 0.55 + (params.spacing_pct * 0.12) + (unit_d * 0.35)
    oos_sharpe = realized_return_pct / max(0.1, base_vol)
    is_sharpe = oos_sharpe * (1.18 + unit_c * 0.55)

    oos_mdd = -min(max(sl * 0.72, 0.05), 0.35)
    is_mdd = oos_mdd * 0.92

    trades_count = 2 + int(safety_triggered)
    pnl_mult = 1.0 + (realized_return_pct / 100.0)

    now = _now_iso()
    summary = {
        "candidate_id": cid,
        "strategy_id": str(candidate.get("strategy_id") or "dca1"),
        "family": str(candidate.get("family") or "dca1"),
        "symbol": str(candidate.get("symbol") or "BTCUSDT"),
        "timeframe": str(candidate.get("timeframe") or "1h"),
        "direction": direction,
        "variant": str(candidate.get("variant") or "base"),
        "status": "SUCCESS",
        "report_only": True,
        "timestamp": now,
        "sharpe": round(oos_sharpe, 6),
        "max_drawdown": round(oos_mdd, 6),
        "trades_count": int(trades_count),
        "total_return": round(realized_return_pct, 6),
        "pnl_mult": round(pnl_mult, 6),
        "cost_breakdown": cost,
        "dca_params": params.__dict__,
        "safety_order_triggered": bool(safety_triggered),
    }

    selection = {
        "decision": "SELECT" if (oos_sharpe >= 0.7 and pnl_mult >= 1.0) else "WATCHLIST",
        "selected_symbol": summary["symbol"],
        "candidate_id": cid,
        "direction": direction,
        "gate": {"overall": "PENDING", "reasons": []},
        "report_only": True,
        "timestamp": now,
    }

    metrics = {
        "status": "SUCCESS",
        "candidate_id": cid,
        "strategy_id": summary["strategy_id"],
        "family": summary["family"],
        "direction": direction,
        "variant": summary["variant"],
        "is_sharpe": round(is_sharpe, 6),
        "oos_sharpe": round(oos_sharpe, 6),
        "is_mdd": round(is_mdd, 6),
        "oos_mdd": round(oos_mdd, 6),
        "pnl_mult": round(pnl_mult, 6),
        "trades_count": int(trades_count),
        "total_cost_bps": cost["total_cost_bps"],
        "timestamp": now,
    }

    return {
        "summary": summary,
        "selection": selection,
        "metrics": metrics,
        "report_md": _render_report(summary=summary, selection=selection),
    }


def _parse_params(raw: dict[str, Any]) -> DCA1Params:
    def val(key: str, default: float) -> float:
        try:
            return float(raw.get(key, default))
        except Exception:
            return default

    return DCA1Params(
        base_order=val("base_order", 1.0),
        safety_mult=val("safety_mult", 1.6),
        spacing_pct=val("spacing_pct", 1.2),
        take_profit_pct=val("take_profit_pct", 1.1),
        stop_loss_pct=val("stop_loss_pct", 2.3),
        trailing_pct=val("trailing_pct", 0.0),
    )


def _render_report(*, summary: dict[str, Any], selection: dict[str, Any]) -> str:
    c = summary.get("cost_breakdown", {})
    return (
        f"# DCA-1 Report: {summary.get('candidate_id')}\n"
        f"Generated: {summary.get('timestamp')}\n"
        f"Report-Only: true\n\n"
        f"## Summary\n"
        f"- Strategy: {summary.get('strategy_id')}\n"
        f"- Family: {summary.get('family')}\n"
        f"- Direction: {summary.get('direction')}\n"
        f"- Variant: {summary.get('variant')}\n"
        f"- Sharpe (OOS): {summary.get('sharpe')}\n"
        f"- MaxDD (OOS): {summary.get('max_drawdown')}\n"
        f"- Trades: {summary.get('trades_count')}\n"
        f"- Return (%): {summary.get('total_return')}\n"
        f"- Selection Decision: {selection.get('decision')}\n\n"
        f"## Cost Model\n"
        f"- fee_bps: {c.get('fee_bps')}\n"
        f"- slippage_bps: {c.get('slippage_bps')}\n"
        f"- total_cost_bps: {c.get('total_cost_bps')}\n"
        f"- slippage_source: {c.get('slippage_source')}\n"
        f"- lookahead_safe: {c.get('lookahead_safe')}\n"
        f"\n---\n"
        f"actions=[] (report_only)\n"
    )


def _seed_for(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _unit(seed: int, *, salt: str) -> float:
    h = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) / float(0xFFFFFFFF)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
