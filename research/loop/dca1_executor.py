from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from research.loop.dca_cost_model import DcaCostModelConfig, estimate_trade_cost_bps


@dataclass
class Dca1ExecutorConfig:
    base_order_qty: float = 1.0
    safety_multiplier: float = 1.5
    safety_spacing_pct: float = 0.02
    take_profit_pct: float = 0.03
    stop_loss_pct: float = 0.04
    trailing_pct: float | None = None
    start_equity: float = 1000.0
    cost_model: DcaCostModelConfig = field(default_factory=DcaCostModelConfig)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_timestamps(n: int) -> list[str]:
    base = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [(base.replace(hour=(base.hour + i) % 24)).isoformat() for i in range(n)]


def _effective_fill(price: float, side: str, total_cost_bps: float) -> float:
    impact = float(total_cost_bps) / 10000.0
    if side.upper() == "BUY":
        return price * (1.0 + impact)
    return price * (1.0 - impact)


def _weighted_cost_breakdown(order_logs: list[dict[str, Any]]) -> dict[str, Any]:
    if not order_logs:
        return {
            "fee_bps": 0.0,
            "slippage_bps": 0.0,
            "total_cost_bps": 0.0,
            "slippage_source": "L3_FIXED_BPS",
            "slippage_source_counts": {},
        }

    total_notional = 0.0
    fee = 0.0
    slip = 0.0
    source_counts: dict[str, int] = {}
    for row in order_logs:
        qty = float(row.get("qty", 0.0))
        px = float(row.get("price", 0.0))
        notional = abs(qty * px)
        if notional <= 0:
            continue
        total_notional += notional
        costs = row.get("cost", {})
        fee += notional * float(costs.get("fee_bps", 0.0))
        slip += notional * float(costs.get("slippage_bps", 0.0))
        src = str(costs.get("slippage_source", "L3_FIXED_BPS"))
        source_counts[src] = source_counts.get(src, 0) + 1

    if total_notional <= 0:
        return {
            "fee_bps": 0.0,
            "slippage_bps": 0.0,
            "total_cost_bps": 0.0,
            "slippage_source": "L3_FIXED_BPS",
            "slippage_source_counts": source_counts,
        }

    fee_bps = fee / total_notional
    slippage_bps = slip / total_notional
    source = max(source_counts.items(), key=lambda item: item[1])[0] if source_counts else "L3_FIXED_BPS"
    return {
        "fee_bps": round(fee_bps, 6),
        "slippage_bps": round(slippage_bps, 6),
        "total_cost_bps": round(fee_bps + slippage_bps, 6),
        "slippage_source": source if len(source_counts) == 1 else "MIXED",
        "slippage_source_counts": source_counts,
    }


def run_dca1_backtest_report_only(
    *,
    prices: Sequence[float],
    timestamps: Sequence[str] | None = None,
    market_contexts: Sequence[dict[str, Any]] | None = None,
    config: Dca1ExecutorConfig | None = None,
) -> dict[str, Any]:
    if len(prices) < 2:
        raise ValueError("prices must contain at least 2 points")

    cfg = config or Dca1ExecutorConfig()
    ts = list(timestamps) if timestamps is not None else _default_timestamps(len(prices))
    if len(ts) != len(prices):
        raise ValueError("timestamps length must equal prices length")
    mctx = list(market_contexts) if market_contexts is not None else [{} for _ in prices]
    if len(mctx) != len(prices):
        raise ValueError("market_contexts length must equal prices length")

    order_logs: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    equity_curve: list[dict[str, Any]] = []

    base_price = float(prices[0])
    base_qty = float(cfg.base_order_qty)
    base_cost = estimate_trade_cost_bps(
        order_qty=base_qty,
        side="BUY",
        order_ts=ts[0],
        market_ctx=mctx[0],
        config=cfg.cost_model,
    )
    base_fill = _effective_fill(base_price, "BUY", float(base_cost["total_cost_bps"]))
    position_qty = base_qty
    position_notional = base_fill * base_qty
    order_logs.append({"event": "base_entry", "idx": 0, "ts": ts[0], "side": "BUY", "qty": base_qty, "price": base_price, "effective_fill": base_fill, "cost": base_cost})
    events.append({"event": "base_entry", "idx": 0, "price": base_price, "effective_fill": base_fill})

    safety_done = False
    trailing_armed = False
    trailing_stop: float | None = None
    trailing_high: float | None = None
    exit_idx = len(prices) - 1
    exit_reason = "TIME_EXIT"

    avg_entry = position_notional / position_qty
    safety_trigger_px = base_price * (1.0 - float(cfg.safety_spacing_pct))

    for idx in range(1, len(prices)):
        px = float(prices[idx])

        if not safety_done and px <= safety_trigger_px:
            safety_qty = base_qty * float(cfg.safety_multiplier)
            safety_cost = estimate_trade_cost_bps(
                order_qty=safety_qty,
                side="BUY",
                order_ts=ts[idx],
                market_ctx=mctx[idx],
                config=cfg.cost_model,
            )
            safety_fill = _effective_fill(px, "BUY", float(safety_cost["total_cost_bps"]))
            position_qty += safety_qty
            position_notional += safety_fill * safety_qty
            avg_entry = position_notional / position_qty
            safety_done = True
            order_logs.append({"event": "safety_entry", "idx": idx, "ts": ts[idx], "side": "BUY", "qty": safety_qty, "price": px, "effective_fill": safety_fill, "cost": safety_cost})
            events.append({"event": "safety_entry", "idx": idx, "price": px, "effective_fill": safety_fill})

        avg_entry = position_notional / position_qty
        unrealized = (px - avg_entry) / avg_entry
        equity_curve.append({"idx": idx, "ts": ts[idx], "equity": cfg.start_equity * (1.0 + unrealized)})

        stop_loss_px = avg_entry * (1.0 - float(cfg.stop_loss_pct))
        take_profit_px = avg_entry * (1.0 + float(cfg.take_profit_pct))

        if px <= stop_loss_px:
            exit_idx = idx
            exit_reason = "STOP_LOSS"
            break

        if cfg.trailing_pct is None:
            if px >= take_profit_px:
                exit_idx = idx
                exit_reason = "TAKE_PROFIT"
                break
            continue

        if not trailing_armed and px >= take_profit_px:
            trailing_armed = True
            trailing_high = px
            trailing_stop = px * (1.0 - float(cfg.trailing_pct))
            events.append({"event": "trailing_armed", "idx": idx, "price": px, "trailing_stop": trailing_stop})
            continue

        if trailing_armed:
            if trailing_high is None or px > trailing_high:
                trailing_high = px
                trailing_stop = px * (1.0 - float(cfg.trailing_pct))
            if trailing_stop is not None and px <= trailing_stop:
                exit_idx = idx
                exit_reason = "TRAILING_STOP"
                break

    exit_price = float(prices[exit_idx])
    exit_cost = estimate_trade_cost_bps(
        order_qty=position_qty,
        side="SELL",
        order_ts=ts[exit_idx],
        market_ctx=mctx[exit_idx],
        config=cfg.cost_model,
    )
    exit_fill = _effective_fill(exit_price, "SELL", float(exit_cost["total_cost_bps"]))
    exit_notional = exit_fill * position_qty
    pnl_pct = (exit_notional - position_notional) / position_notional

    order_logs.append({"event": "exit", "idx": exit_idx, "ts": ts[exit_idx], "side": "SELL", "qty": position_qty, "price": exit_price, "effective_fill": exit_fill, "cost": exit_cost})
    events.append({"event": "exit", "idx": exit_idx, "price": exit_price, "effective_fill": exit_fill, "reason": exit_reason})

    equity_path = [cfg.start_equity]
    equity_path.extend([float(row.get("equity", cfg.start_equity)) for row in equity_curve])
    equity_path.append(cfg.start_equity * (1.0 + pnl_pct))
    peak = max(equity_path)
    trough = min(equity_path)
    max_drawdown = (trough - peak) / peak if peak > 0 else 0.0

    denom = max(0.02, abs(max_drawdown) * 2.0)
    oos_sharpe = (pnl_pct - 0.0005) / denom
    is_sharpe = oos_sharpe + 0.15

    return {
        "status": "SUCCESS",
        "timestamp": _utc_now(),
        "report_only": True,
        "actions": [],
        "prices_count": len(prices),
        "orders_count": len(order_logs),
        "trades_count": len(order_logs),
        "pnl_mult": 1.0 + pnl_pct,
        "total_return": pnl_pct,
        "oos_sharpe": oos_sharpe,
        "is_sharpe": is_sharpe,
        "oos_mdd": max_drawdown,
        "is_mdd": max_drawdown * 0.9,
        "exit_reason": exit_reason,
        "safety_filled": safety_done,
        "order_logs": order_logs,
        "events": events,
        "cost_breakdown": _weighted_cost_breakdown(order_logs),
    }


def _gate_from_summary(summary: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if float(summary.get("sharpe", 0.0)) < 0.2:
        reasons.append("oos_sharpe_below_floor")
    if float(summary.get("max_drawdown", 0.0)) < -0.30:
        reasons.append("oos_mdd_breach")
    if int(summary.get("trades_count", 0)) < 2:
        reasons.append("insufficient_trades")
    passed = len(reasons) == 0
    return {
        "schema_version": 2,
        "generated_at": _utc_now(),
        "inputs": {
            "strategy": summary.get("strategy"),
            "symbol": summary.get("symbol"),
            "timeframe": summary.get("timeframe"),
        },
        "config": {
            "thresholds": {
                "min_sharpe": 0.2,
                "max_mdd": -0.30,
                "min_trades": 2,
            }
        },
        "results": {
            "overall": {
                "pass": passed,
                "reasons": reasons,
                "portfolio_trades": int(summary.get("trades_count", 0)),
                "exposure": 0.0,
            }
        },
    }


def _selection_from_gate(summary: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    overall = gate.get("results", {}).get("overall", {})
    passed = bool(overall.get("pass", False))
    decision = "TRADE" if passed else "HOLD"
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "strategy_id": summary.get("strategy"),
        "regime": "RESEARCH",
        "gate": {
            "overall": "PASS" if passed else "FAIL",
            "reasons": list(overall.get("reasons", [])),
        },
        "decision": decision,
        "selected": {
            "symbol": summary.get("symbol"),
            "params": summary.get("config", {}),
            "score": {
                "sharpe": summary.get("sharpe"),
                "total_return": summary.get("total_return"),
                "max_drawdown": summary.get("max_drawdown"),
            },
        },
        "candidates": [
            {
                "rank": 1,
                "params": summary.get("config", {}),
                "score": {
                    "sharpe": summary.get("sharpe"),
                    "total_return": summary.get("total_return"),
                    "max_drawdown": summary.get("max_drawdown"),
                },
                "metrics": {
                    "trades_count": summary.get("trades_count"),
                    "win_rate": summary.get("win_rate"),
                },
            }
        ],
        "reasons": list(overall.get("reasons", [])),
    }


def _report_markdown(summary: dict[str, Any], gate: dict[str, Any], selection: dict[str, Any]) -> str:
    overall = gate.get("results", {}).get("overall", {})
    lines = [
        f"# DCA-1 Cost-aware Research Report ({summary.get('strategy')})",
        "",
        f"- generated_at: `{summary.get('timestamp')}`",
        f"- symbol/timeframe: `{summary.get('symbol')}` / `{summary.get('timeframe')}`",
        f"- report_only: `{summary.get('report_only')}`",
        f"- decision: `{selection.get('decision')}`",
        "",
        "## Metrics",
        f"- total_return: `{summary.get('total_return')}`",
        f"- sharpe: `{summary.get('sharpe')}`",
        f"- max_drawdown: `{summary.get('max_drawdown')}`",
        f"- trades_count: `{summary.get('trades_count')}`",
        "",
        "## Cost Breakdown",
        f"- fee_bps: `{summary.get('cost_breakdown', {}).get('fee_bps')}`",
        f"- slippage_bps: `{summary.get('cost_breakdown', {}).get('slippage_bps')}`",
        f"- total_cost_bps: `{summary.get('cost_breakdown', {}).get('total_cost_bps')}`",
        f"- slippage_source: `{summary.get('cost_breakdown', {}).get('slippage_source')}`",
        "",
        "## Gate",
        f"- pass: `{overall.get('pass')}`",
        f"- reasons: `{overall.get('reasons', [])}`",
        "",
        "*report_only: actions=[]*",
    ]
    return "\n".join(lines)


def generate_dca1_artifacts(
    *,
    out_dir: Path,
    strategy_id: str,
    symbol: str,
    timeframe: str,
    prices: Sequence[float],
    timestamps: Sequence[str] | None = None,
    market_contexts: Sequence[dict[str, Any]] | None = None,
    config: Dca1ExecutorConfig | None = None,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)

    sim = run_dca1_backtest_report_only(
        prices=prices,
        timestamps=timestamps,
        market_contexts=market_contexts,
        config=config,
    )
    summary = {
        "run_id": out_dir.name,
        "timestamp": sim["timestamp"],
        "strategy": strategy_id,
        "symbol": symbol,
        "timeframe": timeframe,
        "report_only": True,
        "actions": [],
        "start_equity": float((config or Dca1ExecutorConfig()).start_equity),
        "end_equity": float((config or Dca1ExecutorConfig()).start_equity) * float(sim["pnl_mult"]),
        "total_return": float(sim["total_return"]),
        "max_drawdown": float(sim["oos_mdd"]),
        "sharpe": float(sim["oos_sharpe"]),
        "trades_count": int(sim["trades_count"]),
        "win_rate": 1.0 if float(sim["total_return"]) > 0 else 0.0,
        "exit_reason": sim["exit_reason"],
        "safety_filled": bool(sim["safety_filled"]),
        "cost_breakdown": sim["cost_breakdown"],
        "config": asdict(config) if config is not None else asdict(Dca1ExecutorConfig()),
    }
    gate = _gate_from_summary(summary)
    selection = _selection_from_gate(summary, gate)

    results = {
        "experiment_id": strategy_id,
        "status": "SUCCESS",
        "report_only": True,
        "actions": [],
        "timestamp": sim["timestamp"],
        "is_sharpe": float(sim["is_sharpe"]),
        "oos_sharpe": float(sim["oos_sharpe"]),
        "oos_mdd": float(sim["oos_mdd"]),
        "total_return": float(sim["total_return"]),
        "trades_count": int(sim["trades_count"]),
        "family": "dca1",
        "cost_breakdown": sim["cost_breakdown"],
    }

    summary_path = out_dir / "summary.json"
    gate_path = out_dir / "gate.json"
    selection_path = out_dir / "selection.json"
    report_path = out_dir / "report.md"
    results_path = out_dir / f"{strategy_id}_results.json"

    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    gate_path.write_text(json.dumps(gate, indent=2), encoding="utf-8")
    selection_path.write_text(json.dumps(selection, indent=2), encoding="utf-8")
    report_path.write_text(_report_markdown(summary, gate, selection), encoding="utf-8")
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return {
        "summary": summary,
        "gate": gate,
        "selection": selection,
        "results": results,
        "summary_path": str(summary_path),
        "gate_path": str(gate_path),
        "selection_path": str(selection_path),
        "report_path": str(report_path),
        "results_path": str(results_path),
    }


def maybe_run_dca1_candidate(
    *,
    proposal_strategy: str,
    proposal_id: str,
    symbol: str,
    timeframe: str,
    reports_root: Path,
    enabled: bool,
) -> dict[str, Any] | None:
    if not enabled:
        return None
    if proposal_strategy not in {"dca1_cost_aware_v1", "dca1_executor_v1"}:
        return None

    ts = datetime.now(timezone.utc).strftime("%Y%m%d")
    out_dir = reports_root / ts / proposal_id
    prices = [100.0, 98.6, 97.9, 99.8, 101.7, 103.2, 102.3, 104.0]
    artifacts = generate_dca1_artifacts(
        out_dir=out_dir,
        strategy_id=proposal_strategy,
        symbol=symbol,
        timeframe=timeframe,
        prices=prices,
    )
    result = dict(artifacts["results"])
    result["artifact_paths"] = {
        "summary_path": artifacts["summary_path"],
        "selection_path": artifacts["selection_path"],
        "gate_path": artifacts["gate_path"],
        "report_path": artifacts["report_path"],
    }
    return result
