#!/usr/bin/env python3
"""
HONGSTR Autonomous Research Loop v2
Cycle: Observe -> Propose -> Validate -> Run -> Gate -> Report -> Leaderboard -> Notify.

Stability-first constraints:
  - Actions are always [] (report_only)
  - Failures degrade to status=WARN, exit 0 (never block ETL/dashboard/tg_cp)
  - Lock prevents re-entry; stale lock (>TTL_HOURS) is auto-released
  - No .parquet/.pkl ever written to git-tracked paths
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RESEARCH_STATE_DIR = REPO_ROOT / "data/state/_research"
REPORTS_ROOT = REPO_ROOT / "reports/research"
REGISTRY_PATH = REPO_ROOT / "research/experiments/registry.json"
LOCK_PATH = RESEARCH_STATE_DIR / "loop_lock.json"
STATE_PATH = RESEARCH_STATE_DIR / "loop_state.json"
STRATEGY_POOL_PATH = REPO_ROOT / "data/state/strategy_pool.json"
NOTIFY_SH = REPO_ROOT / "scripts/notify_telegram.sh"

RESEARCH_STATE_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
LOCK_TTL_HOURS = 2

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(RESEARCH_STATE_DIR / "loop.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("research_loop")

# ── Late imports (after path setup) ───────────────────────────────────────────
from research.loop.candidate_catalog import build_candidate_catalog, summarize_catalog
from research.loop.dca1_executor import run_dca1_candidate
from research.loop.gates import ResearchGate
from research.loop.leaderboard import save_leaderboard
from research.loop.regime_timeline import resolve_regime_context
from research.loop.schemas_research import ResearchProposal
from research.loop.weekly_governance import generate_weekly_quant_checklist


# ── Lock ──────────────────────────────────────────────────────────────────────
def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def acquire_lock() -> bool:
    """Acquire a process lock. Returns True if acquired, False if already locked by live process."""
    if LOCK_PATH.exists():
        try:
            lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            pid = lock.get("pid")
            start_ts = lock.get("start_ts", 0)
            ttl_hours = lock.get("ttl_hours", LOCK_TTL_HOURS)
            age_hours = (_now_ts() - start_ts) / 3600
            if age_hours < ttl_hours:
                try:
                    os.kill(pid, 0)
                    logger.warning("Loop already running (pid=%s, age=%.1fh). Skipping.", pid, age_hours)
                    return False
                except (ProcessLookupError, PermissionError):
                    logger.info("Stale lock (pid=%s no longer running). Auto-releasing.", pid)
            else:
                logger.info("Stale lock (age=%.1fh > TTL=%sh). Auto-releasing.", age_hours, ttl_hours)
        except Exception as e:
            logger.warning("Could not parse lock file: %s. Overwriting.", e)

    LOCK_PATH.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "start_ts": _now_ts(),
                "ttl_hours": LOCK_TTL_HOURS,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    logger.info("Lock acquired (pid=%s).", os.getpid())
    return True


def release_lock() -> None:
    """Release the process lock if it belongs to us."""
    try:
        if LOCK_PATH.exists():
            lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
            if lock.get("pid") == os.getpid():
                LOCK_PATH.unlink()
                logger.info("Lock released.")
    except Exception as e:
        logger.warning("Could not release lock: %s", e)


# ── State ─────────────────────────────────────────────────────────────────────
def write_state(
    status: str,
    exp_id: str | None = None,
    gate_passed: bool | None = None,
    report_path: str | None = None,
    error: str | None = None,
) -> None:
    """Write enriched loop_state.json. actions is always []."""
    state = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "last_exp": exp_id,
        "gate_passed": gate_passed,
        "report_path": report_path,
        "error": error,
        "actions": [],
    }
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    logger.info("State written: status=%s", status)


# ── Registry + Candidate Simulation ───────────────────────────────────────────
def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def run_backtest_simulated(
    proposal: ResearchProposal,
    dry_run: bool = False,
    *,
    candidate: dict[str, Any] | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministic simulated OOS/WF backtest for non-DCA candidates (report_only)."""
    if dry_run:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "status": "DRY_RUN",
            "is_sharpe": 0.0,
            "oos_sharpe": 0.0,
            "is_mdd": 0.0,
            "oos_mdd": 0.0,
            "pnl_mult": 1.0,
            "trades_count": 0,
            "total_cost_bps": 0.0,
            "timestamp": now,
            "direction": (candidate or {}).get("direction", "LONG"),
            "variant": (candidate or {}).get("variant", "base"),
            "family": (candidate or {}).get("family", "trend"),
            "strategy_id": proposal.strategy,
            "candidate_id": (candidate or {}).get("candidate_id", proposal.experiment_id),
        }

    cand = candidate or {}
    cid = str(cand.get("candidate_id") or proposal.experiment_id)
    direction = str(cand.get("direction") or "LONG").upper()
    family = str(cand.get("family") or "trend")
    variant = str(cand.get("variant") or "base")

    seed = _seed_for(cid)
    u_a = _unit(seed, "a")
    u_b = _unit(seed, "b")
    u_c = _unit(seed, "c")

    family_bias = {
        "trend": 0.95,
        "mr": 0.85,
        "vol": 0.9,
        "dca1": 0.88,
    }.get(family, 0.85)

    direction_bias = {
        "LONG": 1.0,
        "SHORT": 1.03,
        "LONGSHORT": 1.08,
    }.get(direction, 1.0)

    oos_sharpe = (0.45 + u_a * 1.25) * family_bias * direction_bias
    is_sharpe = oos_sharpe * (1.15 + u_b * 0.65)

    base_mdd = -0.06 - (u_c * 0.18)
    if direction == "LONGSHORT":
        base_mdd *= 0.9
    oos_mdd = max(-0.38, base_mdd)
    is_mdd = oos_mdd * 0.9

    trades_count = int(15 + (u_b * 75))
    pnl_mult = 1.0 + (oos_sharpe * 0.045) + (oos_mdd * 0.18)

    spread_bps = _safe_float((snapshot or {}).get("market_stats", {}).get("spread_bps"), 6.0)
    vol_pct = _safe_float((snapshot or {}).get("market_stats", {}).get("realized_vol_pct"), 1.8)
    total_cost_bps = max(3.0, (spread_bps * 0.7) + (vol_pct * 2.2))

    return {
        "status": "SUCCESS",
        "is_sharpe": round(is_sharpe, 6),
        "oos_sharpe": round(oos_sharpe, 6),
        "is_mdd": round(is_mdd, 6),
        "oos_mdd": round(oos_mdd, 6),
        "pnl_mult": round(pnl_mult, 6),
        "trades_count": trades_count,
        "total_cost_bps": round(total_cost_bps, 6),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "direction": direction,
        "variant": variant,
        "family": family,
        "strategy_id": proposal.strategy,
        "candidate_id": cid,
    }


# ── Artifact / Reporting helpers ─────────────────────────────────────────────
def _regime_meta(regime_context: dict[str, Any] | None) -> dict[str, Any]:
    ctx = regime_context or {}
    applied = str(ctx.get("applied") or "ALL").upper()
    requested = str(ctx.get("requested") or applied).upper()
    return {
        "regime": applied,
        "regime_slice": applied,
        "regime_requested": requested,
        "regime_window_start_utc": ctx.get("window_start_utc"),
        "regime_window_end_utc": ctx.get("window_end_utc"),
        "regime_window_end_exclusive": True,
        "regime_policy_path": ctx.get("policy_path"),
        "regime_status": str(ctx.get("status") or "UNKNOWN").upper(),
        "regime_rationale": str(ctx.get("rationale") or "none"),
    }


def _with_regime_meta(payload: dict[str, Any], regime_context: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(payload)
    out.update(_regime_meta(regime_context))
    return out


def _build_summary(
    candidate: dict[str, Any],
    metrics: dict[str, Any],
    *,
    regime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary = {
        "experiment_id": candidate.get("experiment_id", candidate.get("candidate_id")),
        "candidate_id": candidate.get("candidate_id"),
        "strategy_id": candidate.get("strategy_id"),
        "family": candidate.get("family"),
        "symbol": candidate.get("symbol"),
        "timeframe": candidate.get("timeframe"),
        "direction": candidate.get("direction"),
        "variant": candidate.get("variant"),
        "status": metrics.get("status", "UNKNOWN"),
        "report_only": True,
        "timestamp": metrics.get("timestamp"),
        "sharpe": metrics.get("oos_sharpe", 0.0),
        "is_sharpe": metrics.get("is_sharpe", 0.0),
        "max_drawdown": metrics.get("oos_mdd", 0.0),
        "is_mdd": metrics.get("is_mdd", 0.0),
        "trades_count": metrics.get("trades_count", 0),
        "total_return": round((metrics.get("pnl_mult", 1.0) - 1.0) * 100.0, 6),
        "pnl_mult": metrics.get("pnl_mult", 1.0),
        "total_cost_bps": metrics.get("total_cost_bps", 0.0),
        "parameters": candidate.get("parameters", {}),
    }
    return _with_regime_meta(summary, regime_context)


def _build_selection(
    summary: dict[str, Any],
    gate_payload: dict[str, Any],
    *,
    regime_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recommendation = str(gate_payload.get("recommendation", "WATCHLIST")).upper()
    decision = "SELECT" if recommendation == "PROMOTE" else "WATCHLIST" if recommendation == "WATCHLIST" else "DROP"
    return {
        **_with_regime_meta(
            {
                "decision": decision,
                "selected_symbol": summary.get("symbol", "BTCUSDT"),
                "candidate_id": summary.get("candidate_id"),
                "strategy_id": summary.get("strategy_id"),
                "direction": summary.get("direction", "LONG"),
                "variant": summary.get("variant", "base"),
                "gate": {
                    "overall": gate_payload.get("overall", "UNKNOWN"),
                    "reasons": gate_payload.get("reasons", []),
                    "final_score": gate_payload.get("final_score", 0.0),
                    "recommendation": recommendation,
                },
                "report_only": True,
                "timestamp": summary.get("timestamp"),
            },
            regime_context,
        )
    }


def _render_candidate_report(*, summary: dict[str, Any], gate_payload: dict[str, Any], proposal: ResearchProposal) -> str:
    gate_status = gate_payload.get("overall", "UNKNOWN")
    reasons = gate_payload.get("reasons", [])
    reasons_line = ", ".join(str(r) for r in reasons) if reasons else "none"
    return (
        f"# Research Report: {summary.get('candidate_id')}\n"
        f"Generated: {summary.get('timestamp')}\n"
        f"Report-Only: true\n"
        f"Gate Status: {gate_status}\n\n"
        f"## Candidate\n"
        f"- Strategy: {summary.get('strategy_id')}\n"
        f"- Family: {summary.get('family')}\n"
        f"- Direction: {summary.get('direction')}\n"
        f"- Variant: {summary.get('variant')}\n"
        f"- Regime Slice: {summary.get('regime_slice', 'ALL')}\n"
        f"- Regime Window [start,end): {summary.get('regime_window_start_utc')} -> {summary.get('regime_window_end_utc')}\n"
        f"- Regime Rationale: {summary.get('regime_rationale', 'none')}\n"
        f"- Symbol/TF: {summary.get('symbol')} {summary.get('timeframe')}\n\n"
        f"## Metrics\n"
        f"- OOS Sharpe: {summary.get('sharpe')}\n"
        f"- OOS MaxDD: {summary.get('max_drawdown')}\n"
        f"- Trades: {summary.get('trades_count')}\n"
        f"- PnL Mult: {summary.get('pnl_mult')}\n"
        f"- Cost (bps): {summary.get('total_cost_bps')}\n"
        f"- Final Score: {gate_payload.get('final_score', 0.0)}\n"
        f"- Recommendation: {gate_payload.get('recommendation', 'WATCHLIST')}\n\n"
        f"## Proposal\n"
        f"{proposal.hypothesis}\n\n"
        f"## Gate Reasons\n"
        f"{reasons_line}\n\n"
        f"---\n"
        f"actions=[] (report_only)\n"
    )


def _write_candidate_artifacts(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    gate_payload: dict[str, Any],
    selection: dict[str, Any],
    report_md: str,
    metrics: dict[str, Any],
) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (run_dir / "gate.json").write_text(json.dumps(gate_payload, indent=2), encoding="utf-8")
    (run_dir / "selection.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    report_path = run_dir / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    # Backward compatibility for old leaderboard scanner.
    legacy = dict(metrics)
    legacy.update(
        {
            "candidate_id": summary.get("candidate_id"),
            "strategy_id": summary.get("strategy_id"),
            "family": summary.get("family"),
            "direction": summary.get("direction"),
            "variant": summary.get("variant"),
            "regime": summary.get("regime", "ALL"),
            "regime_slice": summary.get("regime_slice", "ALL"),
            "regime_window_start_utc": summary.get("regime_window_start_utc"),
            "regime_window_end_utc": summary.get("regime_window_end_utc"),
            "final_score": gate_payload.get("final_score", 0.0),
            "gate_overall": gate_payload.get("overall", "UNKNOWN"),
        }
    )
    (run_dir.parent / f"{summary.get('candidate_id')}_results.json").write_text(
        json.dumps(legacy, indent=2),
        encoding="utf-8",
    )
    return report_path


def _write_strategy_pool(records: list[dict[str, Any]]) -> Path:
    ranked = sorted(records, key=lambda x: float(x.get("last_score", 0.0)), reverse=True)
    promoted = [r["candidate_id"] for r in ranked if r.get("recommendation") == "PROMOTE"][:3]
    demoted = [r["candidate_id"] for r in ranked if r.get("recommendation") == "DEMOTE"]
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "report_only": True,
        "candidates": ranked,
        "promoted": promoted,
        "demoted": demoted,
    }
    STRATEGY_POOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    STRATEGY_POOL_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return STRATEGY_POOL_PATH


# ── Telegram Notify ───────────────────────────────────────────────────────────
def notify_telegram(proposal_or_record: Any, gate_passed: bool, report_path: Path, status: str) -> None:
    """Send a brief Telegram summary via notify_telegram.sh (non-blocking)."""
    if not NOTIFY_SH.exists():
        logger.warning("notify_telegram.sh not found, skipping Telegram notify.")
        return

    gate_icon = "✅" if gate_passed else "❌"
    if hasattr(proposal_or_record, "experiment_id"):
        exp = getattr(proposal_or_record, "experiment_id", "unknown")
        hypothesis = str(getattr(proposal_or_record, "hypothesis", ""))
    elif isinstance(proposal_or_record, dict):
        exp = str(
            proposal_or_record.get("candidate_id")
            or proposal_or_record.get("experiment_id")
            or proposal_or_record.get("strategy_id")
            or "unknown"
        )
        hypothesis = str(proposal_or_record.get("hypothesis") or proposal_or_record.get("strategy_id") or "")
    else:
        exp = "unknown"
        hypothesis = ""

    body = (
        f"📊 Research Loop 完成 | {status}\n"
        f"• 實驗: {exp}\n"
        f"• 假說: {hypothesis[:80]}...\n"
        f"• Gate: {gate_icon} {'PASSED' if gate_passed else 'FAILED'}\n"
        f"• 報告: {report_path.name}\n"
        f"• actions=[] (report_only)"
    )
    try:
        subprocess.run(
            ["bash", str(NOTIFY_SH), "--title", "Research Loop", "--body", body, "--status", status.lower()],
            timeout=15,
            capture_output=True,
        )
        logger.info("Telegram notify sent.")
    except Exception as e:
        logger.warning("Telegram notify failed (non-fatal): %s", e)


def notify_telegram_warn(error_msg: str) -> None:
    """Send WARN notification on failure (non-blocking)."""
    if not NOTIFY_SH.exists():
        return
    body = f"⚠️ Research Loop 失敗 (WARN, actions=[])\n• 原因: {error_msg[:200]}"
    try:
        subprocess.run(
            ["bash", str(NOTIFY_SH), "--title", "Research Loop WARN", "--body", body, "--status", "warn"],
            timeout=15,
            capture_output=True,
        )
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="HONGSTR Autonomous Research Loop v2")
    parser.add_argument("--dry-run", action="store_true", help="Skip backtest, write DRY_RUN state")
    parser.add_argument("--max-candidates", type=int, default=0, help="Optional cap for candidate count")
    parser.add_argument(
        "--regime",
        default=os.getenv("HONGSTR_REGIME_SLICE", "ALL"),
        help="Optional regime slice: ALL|BULL|BEAR|SIDEWAYS (default: env HONGSTR_REGIME_SLICE or ALL)",
    )
    parser.add_argument(
        "--disable-dca-family",
        action="store_true",
        help="Disable DCA candidate family for this run",
    )
    args, _ = parser.parse_known_args()

    logger.info("Research Loop v2 starting (dry_run=%s)...", args.dry_run)

    if not acquire_lock():
        write_state("WARN", error="Loop already running (lock held)")
        raise SystemExit(0)

    try:
        # 1. Observe
        from _local.telegram_cp.tg_cp_server import _collect_snapshot

        snapshot = _collect_snapshot()
        registry = load_registry()

        include_dca = not args.disable_dca_family
        max_candidates = args.max_candidates if args.max_candidates > 0 else None
        catalog = build_candidate_catalog(include_dca=include_dca, max_candidates=max_candidates)
        if not catalog:
            raise RuntimeError("candidate_catalog_empty")

        cat_summary = summarize_catalog(catalog)
        logger.info("Candidate catalog loaded: %s", cat_summary)

        regime_context = resolve_regime_context(args.regime)
        if regime_context.get("status") == "WARN":
            logger.warning(
                "Regime slice WARN: requested=%s applied=%s rationale=%s warnings=%s",
                regime_context.get("requested"),
                regime_context.get("applied"),
                regime_context.get("rationale"),
                regime_context.get("warnings", []),
            )
        else:
            logger.info(
                "Regime slice: requested=%s applied=%s window=[%s,%s)",
                regime_context.get("requested"),
                regime_context.get("applied"),
                regime_context.get("window_start_utc"),
                regime_context.get("window_end_utc"),
            )

        gate = ResearchGate()
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        run_root = REPORTS_ROOT / date_str
        run_root.mkdir(parents=True, exist_ok=True)

        records: list[dict[str, Any]] = []
        representative_report: Path | None = None

        # 2~7. Propose/Validate/Run/Gate/Report for each candidate
        for idx, candidate in enumerate(catalog, start=1):
            candidate = dict(candidate)
            exp_id = f"EXP_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}_{idx:03d}"
            candidate["experiment_id"] = exp_id
            if regime_context.get("applied") != "ALL":
                candidate["backtest_window"] = {
                    "start_utc": regime_context.get("window_start_utc"),
                    "end_utc": regime_context.get("window_end_utc"),
                    "end_exclusive": True,
                }
            proposal_data = {
                "experiment_id": exp_id,
                "priority": "MED",
                "hypothesis": (
                    f"{candidate.get('family')}:{candidate.get('strategy_id')} "
                    f"{candidate.get('direction')} variant={candidate.get('variant')} candidate audit"
                ),
                "strategy": str(candidate.get("strategy_id")),
                "symbol": str(candidate.get("symbol", "BTCUSDT")),
                "timeframe": str(candidate.get("timeframe", "1h")),
                "parameters": candidate.get("parameters", {}),
                "metrics_to_watch": ["oos_sharpe", "oos_mdd", "trades_count", "direction"],
                "reasoning": "Generated by research loop candidate catalog (report_only).",
            }
            proposal_data["parameters"] = dict(proposal_data["parameters"])
            proposal_data["parameters"]["regime_slice"] = regime_context.get("applied", "ALL")
            proposal_data["parameters"]["regime_window_start_utc"] = regime_context.get("window_start_utc")
            proposal_data["parameters"]["regime_window_end_utc"] = regime_context.get("window_end_utc")
            proposal = ResearchProposal(**proposal_data)
            proposal.validate_registry(registry)

            if candidate.get("execution_model") == "dca1":
                dca_out = run_dca1_candidate(candidate, snapshot=snapshot, dry_run=args.dry_run)
                summary = _with_regime_meta(dca_out["summary"], regime_context)
                metrics = _with_regime_meta(dca_out["metrics"], regime_context)
                report_md = dca_out["report_md"]
            else:
                metrics = run_backtest_simulated(proposal, dry_run=args.dry_run, candidate=candidate, snapshot=snapshot)
                metrics = _with_regime_meta(metrics, regime_context)
                summary = _build_summary(candidate, metrics, regime_context=regime_context)
                report_md = ""

            gate_result = gate.evaluate_detailed(metrics)
            gate_payload = {
                "overall": "PASS" if gate_result.passed else "FAIL",
                "reasons": [gate_result.reason] if gate_result.reason else [],
                "hard_failures": gate_result.hard_failures,
                "soft_penalties": gate_result.soft_penalties,
                "final_score": gate_result.final_score,
                "recommendation": gate_result.recommendation,
                "policy_name": gate_result.policy_name,
                "report_only": True,
                "timestamp": summary.get("timestamp"),
            }
            gate_payload = _with_regime_meta(gate_payload, regime_context)

            summary["final_score"] = gate_payload["final_score"]
            summary["gate_overall"] = gate_payload["overall"]

            selection = _build_selection(summary, gate_payload, regime_context=regime_context)
            if candidate.get("execution_model") == "dca1":
                selection_from_dca = dca_out["selection"]
                selection["decision"] = selection_from_dca.get("decision", selection["decision"])

            if not report_md:
                report_md = _render_candidate_report(summary=summary, gate_payload=gate_payload, proposal=proposal)

            run_dir = run_root / str(candidate.get("candidate_id"))
            report_path = _write_candidate_artifacts(
                run_dir=run_dir,
                summary=summary,
                gate_payload=gate_payload,
                selection=selection,
                report_md=report_md,
                metrics=metrics,
            )
            representative_report = representative_report or report_path

            records.append(
                {
                    "strategy_id": summary.get("strategy_id"),
                    "candidate_id": summary.get("candidate_id"),
                    "family": summary.get("family"),
                    "direction": summary.get("direction"),
                    "variant": summary.get("variant"),
                    "regime": summary.get("regime", "ALL"),
                    "regime_slice": summary.get("regime_slice", "ALL"),
                    "regime_window_start_utc": summary.get("regime_window_start_utc"),
                    "regime_window_end_utc": summary.get("regime_window_end_utc"),
                    "last_score": summary.get("final_score", 0.0),
                    "gate_overall": summary.get("gate_overall", "UNKNOWN"),
                    "recommendation": gate_payload.get("recommendation", "WATCHLIST"),
                    "last_oos_metrics": {
                        "sharpe": summary.get("sharpe", 0.0),
                        "return": summary.get("total_return", 0.0),
                        "mdd": summary.get("max_drawdown", 0.0),
                    },
                    "report_dir": str(run_dir),
                    "report_only": True,
                }
            )

        if not records:
            raise RuntimeError("no_candidate_records")

        records = gate.apply_watchlist_floor(records)

        # 8. Side artifacts for SSOT and governance
        pool_path = _write_strategy_pool(records)
        board_path = save_leaderboard(top_n=20)
        weekly = generate_weekly_quant_checklist(
            REPO_ROOT,
            recent_results=[
                {
                    "candidate_id": r.get("candidate_id"),
                    "score": r.get("last_score", 0.0),
                    "recommendation": r.get("recommendation", "WATCHLIST"),
                }
                for r in records[:20]
            ],
        )

        top = sorted(records, key=lambda r: float(r.get("last_score", 0.0)), reverse=True)[0]
        top_pass = bool(str(top.get("gate_overall", "")).upper() == "PASS")

        write_state(
            status="OK" if not args.dry_run else "DRY_RUN",
            exp_id=str(top.get("candidate_id")),
            gate_passed=top_pass,
            report_path=str(representative_report or weekly.get("outputs", {}).get("markdown", "")),
        )

        notify_telegram(top, top_pass, representative_report or Path(weekly.get("outputs", {}).get("markdown", "report.md")), "OK" if not args.dry_run else "DRY_RUN")

        logger.info(
            "Research Loop v2 completed: candidates=%s regime=%s pool=%s board=%s weekly=%s",
            len(records),
            regime_context.get("applied", "ALL"),
            pool_path,
            board_path,
            weekly.get("outputs", {}),
        )

    except Exception as e:
        logger.error("Research Loop failed: %s", e, exc_info=True)
        try:
            write_state("WARN", error=str(e))
        except Exception:
            pass
        notify_telegram_warn(str(e))
        raise SystemExit(0)
    finally:
        release_lock()


# ── Utility ───────────────────────────────────────────────────────────────────
def _seed_for(text: str) -> int:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:16], 16)


def _unit(seed: int, salt: str) -> float:
    h = hashlib.sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) / float(0xFFFFFFFF)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


if __name__ == "__main__":
    main()
