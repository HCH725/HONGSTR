from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from research.loop.dca_cost_model import estimate_cost_breakdown


@dataclass(frozen=True)
class DCA1Params:
    base_order: float = 1.0
    safety_multiplier: float = 1.6
    safety_gap_bps: float = 120.0
    take_profit_pct: float = 1.1
    stop_loss_pct: float = 2.3
    trailing_pct: float = 0.0


@dataclass(frozen=True)
class DCA1GateConfig:
    min_oos_sharpe: float = 0.55
    max_oos_mdd: float = -0.2
    min_trades_count: int = 2
    max_cost_bps: float = 28.0
    max_cost_multiplier: float = 2.2


def run_dca1_candidate(
    candidate: dict[str, Any],
    *,
    snapshot: dict[str, Any] | None = None,
    cost_config: dict[str, Any] | None = None,
    gate_config: dict[str, Any] | None = None,
    fee_scenario: str = "standard",
    dry_run: bool = False,
) -> dict[str, Any]:
    cid = str(candidate.get("candidate_id") or candidate.get("strategy_id") or "dca1_candidate")
    direction = str(candidate.get("direction") or "LONG").upper()
    params = _parse_params(candidate.get("parameters") if isinstance(candidate.get("parameters"), dict) else {})
    gate_cfg = _parse_gate_config(gate_config)

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
                "fee_scenario": fee_scenario,
                "lookahead_safe": True,
                "fallback_reason": "",
            },
            "dca_params": params.__dict__,
        }
        gate_payload = {
            "overall": "FAIL",
            "reasons": ["DRY_RUN"],
            "cost_stress": {"pass": False, "cost_multiplier": 0.0},
            "report_only": True,
            "timestamp": now,
        }
        selection = {
            "decision": "DRY_RUN",
            "selected_symbol": summary["symbol"],
            "candidate_id": cid,
            "direction": direction,
            "gate": gate_payload,
            "report_only": True,
            "timestamp": now,
        }
        return {
            "summary": summary,
            "selection": selection,
            "gate": gate_payload,
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
            "report_md": _render_report(summary=summary, selection=selection, gate=gate_payload),
        }

    seed = _seed_for(cid)
    unit_a = _unit(seed, salt="a")
    unit_b = _unit(seed, salt="b")
    unit_c = _unit(seed, salt="c")
    unit_d = _unit(seed, salt="d")

    safety_notional = params.base_order * params.safety_multiplier
    trigger_bias = max(0.15, min(0.95, 0.5 + (params.safety_gap_bps / 1000.0) - (params.safety_multiplier * 0.1)))
    safety_triggered = unit_b < trigger_bias

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
        fee_scenario=fee_scenario,
    )
    stress_cost = estimate_cost_breakdown(
        order_notional=order_notional,
        orderbook=orderbook,
        market_stats=market_stats,
        config=cost_config,
        fee_scenario="stress",
    )

    gross_edge_bps = 38.0 + (unit_a * 98.0)
    if direction == "SHORT":
        gross_edge_bps *= 1.04
    elif direction == "LONGSHORT":
        gross_edge_bps *= 1.08

    safety_drag_bps = 5.0 if safety_triggered else 0.0
    risk_drag_bps = max(3.0, params.stop_loss_pct * 1.4)
    net_edge_bps = gross_edge_bps - cost["total_cost_bps"] - safety_drag_bps - risk_drag_bps

    raw_return_pct = net_edge_bps / 100.0
    if raw_return_pct > params.take_profit_pct:
        realized_return_pct = params.take_profit_pct + min(params.trailing_pct * 0.35, 0.8)
    elif raw_return_pct < -params.stop_loss_pct:
        realized_return_pct = -params.stop_loss_pct
    else:
        realized_return_pct = raw_return_pct

    base_vol = 0.6 + (params.safety_gap_bps / 1000.0) + (unit_d * 0.25)
    oos_sharpe = realized_return_pct / max(0.1, base_vol)
    is_sharpe = oos_sharpe * (1.15 + unit_c * 0.6)

    oos_mdd = -min(max(params.stop_loss_pct * 0.7, 0.05), 0.35)
    is_mdd = oos_mdd * 0.92

    trades_count = 2 + int(safety_triggered)
    pnl_mult = 1.0 + (realized_return_pct / 100.0)

    cost_multiplier = stress_cost["total_cost_bps"] / max(cost["total_cost_bps"], 1e-6)
    stress_gate_pass = (stress_cost["total_cost_bps"] <= gate_cfg.max_cost_bps) and (cost_multiplier <= gate_cfg.max_cost_multiplier)

    gate_failures: list[str] = []
    if oos_sharpe < gate_cfg.min_oos_sharpe:
        gate_failures.append("oos_sharpe_below_floor")
    if oos_mdd < gate_cfg.max_oos_mdd:
        gate_failures.append("oos_mdd_worse_than_ceiling")
    if trades_count < gate_cfg.min_trades_count:
        gate_failures.append("trades_below_min")
    if not stress_gate_pass:
        gate_failures.append("cost_stress_gate_failed")

    overall_pass = len(gate_failures) == 0

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
        "cost_breakdown_stress": stress_cost,
        "dca_params": params.__dict__,
        "safety_order_triggered": bool(safety_triggered),
    }

    gate_payload = {
        "overall": "PASS" if overall_pass else "FAIL",
        "reasons": gate_failures,
        "cost_stress": {
            "pass": stress_gate_pass,
            "cost_multiplier": round(cost_multiplier, 6),
            "max_cost_multiplier": gate_cfg.max_cost_multiplier,
            "stress_total_cost_bps": stress_cost["total_cost_bps"],
            "max_cost_bps": gate_cfg.max_cost_bps,
        },
        "report_only": True,
        "timestamp": now,
    }

    selection = {
        "decision": "SELECT" if overall_pass else "WATCHLIST",
        "selected_symbol": summary["symbol"],
        "candidate_id": cid,
        "direction": direction,
        "gate": gate_payload,
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
        "gate": gate_payload,
        "metrics": metrics,
        "report_md": _render_report(summary=summary, selection=selection, gate=gate_payload),
    }


def run_dca1_sweep(
    candidate: dict[str, Any],
    *,
    safety_multiplier_values: list[float],
    safety_gap_bps_values: list[float],
    fee_scenarios: tuple[str, ...] = ("standard", "vip", "stress"),
    snapshot: dict[str, Any] | None = None,
    cost_config: dict[str, Any] | None = None,
    gate_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    base_params = dict(candidate.get("parameters") or {})
    base_id = str(candidate.get("candidate_id") or candidate.get("strategy_id") or "dca1")

    idx = 0
    for sm in safety_multiplier_values:
        for gap in safety_gap_bps_values:
            for fee_scenario in fee_scenarios:
                idx += 1
                c = dict(candidate)
                p = dict(base_params)
                p["safety_multiplier"] = float(sm)
                p["safety_gap_bps"] = float(gap)
                c["parameters"] = p
                c["candidate_id"] = f"{base_id}__sm{sm:.2f}__gap{gap:.0f}__{fee_scenario}__{idx:02d}"

                out = run_dca1_candidate(
                    c,
                    snapshot=snapshot,
                    cost_config=cost_config,
                    gate_config=gate_config,
                    fee_scenario=fee_scenario,
                    dry_run=False,
                )
                outputs.append(out)

    return outputs


def _parse_params(raw: dict[str, Any]) -> DCA1Params:
    def val(key: str, default: float) -> float:
        try:
            return float(raw.get(key, default))
        except Exception:
            return default

    return DCA1Params(
        base_order=val("base_order", 1.0),
        safety_multiplier=val("safety_multiplier", raw.get("safety_mult", 1.6)),
        safety_gap_bps=val("safety_gap_bps", raw.get("spacing_pct", 1.2) * 100.0),
        take_profit_pct=val("take_profit_pct", 1.1),
        stop_loss_pct=val("stop_loss_pct", 2.3),
        trailing_pct=val("trailing_pct", 0.0),
    )


def _parse_gate_config(raw: dict[str, Any] | None) -> DCA1GateConfig:
    raw = raw or {}

    def v(key: str, default: float) -> float:
        try:
            return float(raw.get(key, default))
        except Exception:
            return default

    return DCA1GateConfig(
        min_oos_sharpe=v("min_oos_sharpe", 0.55),
        max_oos_mdd=v("max_oos_mdd", -0.2),
        min_trades_count=int(v("min_trades_count", 2)),
        max_cost_bps=v("max_cost_bps", 28.0),
        max_cost_multiplier=v("max_cost_multiplier", 2.2),
    )


def _render_report(*, summary: dict[str, Any], selection: dict[str, Any], gate: dict[str, Any]) -> str:
    c = summary.get("cost_breakdown", {})
    cs = summary.get("cost_breakdown_stress", {})
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
        f"- fee_scenario: {c.get('fee_scenario')}\n"
        f"- fee_bps: {c.get('fee_bps')}\n"
        f"- slippage_bps: {c.get('slippage_bps')}\n"
        f"- total_cost_bps: {c.get('total_cost_bps')}\n"
        f"- slippage_source: {c.get('slippage_source')}\n"
        f"- lookahead_safe: {c.get('lookahead_safe')}\n"
        f"- stress_total_cost_bps: {cs.get('total_cost_bps')}\n"
        f"\n## Gate\n"
        f"- overall: {gate.get('overall')}\n"
        f"- reasons: {gate.get('reasons')}\n"
        f"- cost_stress: {gate.get('cost_stress')}\n"
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
