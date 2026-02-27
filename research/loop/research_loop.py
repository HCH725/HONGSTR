#!/usr/bin/env python3
"""
HONGSTR Autonomous Research Loop v2
Cycle: Observe -> Propose -> Validate -> Run -> Gate -> Report -> Leaderboard -> Notify.

Stability-first constraints:
  - Actions are always [] (report_only)
  - Failures degrade to status=WARN, exit 0 (never block ETL/dashboard/tg_cp)
  - Lock prevents re-entry; stale lock (>TTL_HOURS) is auto-released
  - LLM calls have hard timeout + fallback
  - No .parquet/.pkl ever written to git-tracked paths
"""
import os
import sys
import json
import time
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

RESEARCH_STATE_DIR = REPO_ROOT / "data/state/_research"
REPORTS_ROOT = REPO_ROOT / "reports/research"
REGISTRY_PATH = REPO_ROOT / "research/experiments/registry.json"
LOCK_PATH = RESEARCH_STATE_DIR / "loop_lock.json"
STATE_PATH = RESEARCH_STATE_DIR / "loop_state.json"
LEADERBOARD_PATH = RESEARCH_STATE_DIR / "leaderboard.json"
NOTIFY_SH = REPO_ROOT / "scripts/notify_telegram.sh"

RESEARCH_STATE_DIR.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────
LOCK_TTL_HOURS = 2
LLM_TIMEOUT = int(os.getenv("HONGSTR_LLM_TIMEOUT", "120"))

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
from research.loop.schemas_research import ResearchProposal
from research.loop.gates import ResearchGate
from research.loop.leaderboard import save_leaderboard
from research.loop.weekly_governance import generate_weekly_quant_checklist
from research.loop.dca1_executor import run_dca1_sweep


# ── Lock ──────────────────────────────────────────────────────────────────────

def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()

def acquire_lock() -> bool:
    """Acquire a process lock. Returns True if acquired, False if already locked by live process."""
    if LOCK_PATH.exists():
        try:
            lock = json.loads(LOCK_PATH.read_text())
            pid = lock.get("pid")
            start_ts = lock.get("start_ts", 0)
            ttl_hours = lock.get("ttl_hours", LOCK_TTL_HOURS)
            age_hours = (_now_ts() - start_ts) / 3600
            if age_hours < ttl_hours:
                # Check if the locking process is still alive
                try:
                    os.kill(pid, 0)  # Signal 0: check existence only
                    logger.warning(f"Loop already running (pid={pid}, age={age_hours:.1f}h). Skipping.")
                    return False
                except (ProcessLookupError, PermissionError):
                    logger.info(f"Stale lock (pid={pid} no longer running). Auto-releasing.")
            else:
                logger.info(f"Stale lock (age={age_hours:.1f}h > TTL={ttl_hours}h). Auto-releasing.")
        except Exception as e:
            logger.warning(f"Could not parse lock file: {e}. Overwriting.")
    
    # Write new lock
    LOCK_PATH.write_text(json.dumps({
        "pid": os.getpid(),
        "start_ts": _now_ts(),
        "ttl_hours": LOCK_TTL_HOURS,
    }, indent=2))
    logger.info(f"Lock acquired (pid={os.getpid()}).")
    return True

def release_lock():
    """Release the process lock if it belongs to us."""
    try:
        if LOCK_PATH.exists():
            lock = json.loads(LOCK_PATH.read_text())
            if lock.get("pid") == os.getpid():
                LOCK_PATH.unlink()
                logger.info("Lock released.")
    except Exception as e:
        logger.warning(f"Could not release lock: {e}")


# ── State ─────────────────────────────────────────────────────────────────────

def write_state(status: str, exp_id: Optional[str] = None, gate_passed: Optional[bool] = None,
                report_path: Optional[str] = None, error: Optional[str] = None):
    """Write enriched loop_state.json. actions is always []."""
    state = {
        "last_run": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "last_exp": exp_id,
        "gate_passed": gate_passed,
        "report_path": report_path,
        "error": error,
        "actions": [],  # Hard redline: report_only
    }
    STATE_PATH.write_text(json.dumps(state, indent=2))
    logger.info(f"State written: status={status}")


# ── Registry + Backtest ───────────────────────────────────────────────────────

def load_registry() -> Dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text())

def run_backtest_simulated(proposal: ResearchProposal, dry_run: bool = False) -> Dict[str, Any]:
    """Simulated OOS/WF backtest (report_only). dry_run skips all computation."""
    if dry_run:
        logger.info("DRY-RUN: skipping backtest.")
        return {
            "status": "DRY_RUN",
            "is_sharpe": 0.0,
            "oos_sharpe": 0.0,
            "is_mdd": 0.0,
            "oos_mdd": 0.0,
            "pnl_mult": 1.0,
            "trades_count": 0,
            "total_cost_bps": 0.0,
            "timestamp": datetime.now().isoformat(),
        }
    logger.info(f"Running simulated backtest for {proposal.experiment_id}...")
    time.sleep(1)
    return {
        "status": "SUCCESS",
        "is_sharpe": 1.5,
        "oos_sharpe": 0.8,
        "is_mdd": -0.10,
        "oos_mdd": -0.12,
        "pnl_mult": 1.15,
        "trades_count": 28,
        "total_cost_bps": 8.0,
        "timestamp": datetime.now().isoformat(),
    }


# ── Report ────────────────────────────────────────────────────────────────────

def generate_report(
    proposal: ResearchProposal,
    results: Dict[str, Any],
    gate_passed: bool,
    gate_details: Dict[str, Any] | None = None,
) -> Path:
    date_str = datetime.now().strftime("%Y%m%d")
    daily_dir = REPORTS_ROOT / date_str
    daily_dir.mkdir(parents=True, exist_ok=True)

    (daily_dir / f"{proposal.experiment_id}_proposal.json").write_text(proposal.model_dump_json(indent=2))
    (daily_dir / f"{proposal.experiment_id}_results.json").write_text(json.dumps(results, indent=2))

    report_path = daily_dir / "report.md"
    details = gate_details or {}
    soft_penalties = details.get("soft_penalties", {})
    hard_failures = details.get("hard_failures", [])
    content = f"""# Research Report: {proposal.experiment_id}
Generated: {results['timestamp']}
Gate Status: {"✅ PASSED" if gate_passed else "❌ FAILED"}

## Experiment Summary
- **Strategy**: {proposal.strategy} | **Symbol**: {proposal.symbol} | **Timeframe**: {proposal.timeframe}
- **Gate Policy**: {details.get("policy_name", "unknown")}
- **Final Score**: {details.get("final_score", 0.0)}
- **Recommendation**: {details.get("recommendation", "UNKNOWN")}

## Hypothesis
{proposal.hypothesis}

## Results (OOS/WF Simulated)
| Metric | IS | OOS |
|--------|----|-----|
| Sharpe | {results['is_sharpe']:.2f} | {results['oos_sharpe']:.2f} |
| MDD    | {results['is_mdd']:.2%} | {results['oos_mdd']:.2%} |
| Trades | - | {results.get('trades_count', 0)} |
| PnL Mult | - | {results.get('pnl_mult', 1.0):.2f} |
| Cost (bps) | - | {results.get('total_cost_bps', 0.0):.2f} |

## Gate Detail
- hard_failures: {hard_failures}
- soft_penalties: {soft_penalties}

## Reasoning
{proposal.reasoning}

---
*report_only: No automated deployment occurred. actions=[]*
"""
    report_path.write_text(content)
    logger.info(f"Report: {report_path}")
    return report_path


# ── Telegram Notify ───────────────────────────────────────────────────────────

def notify_telegram(proposal: ResearchProposal, gate_passed: bool, report_path: Path, status: str):
    """Send a brief Telegram summary via notify_telegram.sh (non-blocking)."""
    if not NOTIFY_SH.exists():
        logger.warning("notify_telegram.sh not found, skipping Telegram notify.")
        return
    gate_icon = "✅" if gate_passed else "❌"
    body = (
        f"📊 Research Loop 完成 | {status}\n"
        f"• 實驗: {proposal.experiment_id}\n"
        f"• 假說: {proposal.hypothesis[:80]}...\n"
        f"• Gate: {gate_icon} {'PASSED' if gate_passed else 'FAILED'}\n"
        f"• 報告: {report_path.name}\n"
        f"• actions=[] (report_only)"
    )
    try:
        subprocess.run(
            ["bash", str(NOTIFY_SH), "--title", "Research Loop", "--body", body, "--status", status.lower()],
            timeout=15, capture_output=True,
        )
        logger.info("Telegram notify sent.")
    except Exception as e:
        logger.warning(f"Telegram notify failed (non-fatal): {e}")


def notify_telegram_warn(error_msg: str):
    """Send WARN notification on failure (non-blocking)."""
    if not NOTIFY_SH.exists():
        return
    body = f"⚠️ Research Loop 失敗 (WARN, actions=[])\n• 原因: {error_msg[:200]}"
    try:
        subprocess.run(
            ["bash", str(NOTIFY_SH), "--title", "Research Loop WARN", "--body", body, "--status", "warn"],
            timeout=15, capture_output=True,
        )
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HONGSTR Autonomous Research Loop v2")
    parser.add_argument("--dry-run", action="store_true", help="Skip backtest, write DRY_RUN state")
    parser.add_argument(
        "--enable-dca1-sweep",
        action="store_true",
        help="Optional research-only DCA-1 sweep artifact generation",
    )
    args, _ = parser.parse_known_args()

    logger.info(f"Research Loop v2 starting (dry_run={args.dry_run})...")

    # ── Lock guard ──
    if not acquire_lock():
        write_state("WARN", error="Loop already running (lock held)")
        sys.exit(0)

    try:
        # 1. Observe
        from _local.telegram_cp.tg_cp_server import _collect_snapshot
        snapshot = _collect_snapshot()
        registry = load_registry()

        # 2. Propose (deterministic demo proposal)
        date_id = datetime.now().strftime("%Y%m%d_%H%M")
        regime = snapshot.get("regime_monitor", {})
        regime_status = regime.get("overall", "UNKNOWN")
        proposal_data = {
            "experiment_id": f"EXP_{date_id}",
            "priority": "HIGH" if regime_status == "WARN" else "MED",
            "hypothesis": f"Regime={regime_status}: shorter lookback may reduce MDD under current vol.",
            "strategy": "trend_follower_v1",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "parameters": {"window": 40, "threshold": 0.05},
            "metrics_to_watch": ["oos_sharpe", "oos_mdd"],
            "reasoning": f"Regime monitor reports {regime_status}. Proposal generated by Research Loop v2.",
        }
        proposal = ResearchProposal(**proposal_data)

        # 3. Validate against registry
        proposal.validate_registry(registry)
        logger.info(f"Proposal validated: {proposal.experiment_id}")

        # 4. Run backtest
        results = run_backtest_simulated(proposal, dry_run=args.dry_run)

        # 5. Gate (OOS/WF priority, config-driven hard+soft)
        gate = ResearchGate()
        gate_result = gate.evaluate_detailed(results)
        gate_passed = bool(gate_result) if not args.dry_run else False
        gate_details = gate_result.as_dict()
        results["final_score"] = gate_details.get("final_score", 0.0)
        results["gate_recommendation"] = gate_details.get("recommendation", "WATCHLIST")
        results["policy_name"] = gate_details.get("policy_name", "unknown")

        # 6. Report
        report_path = generate_report(proposal, results, gate_passed, gate_details=gate_details)

        # 6b. Leaderboard + weekly governance checklist (report-only artifacts)
        save_leaderboard(top_n=20)
        generate_weekly_quant_checklist(
            REPO_ROOT,
            recent_results=[
                {
                    "id": proposal.experiment_id,
                    "score": gate_details.get("final_score", 0.0),
                    "recommendation": gate_details.get("recommendation", "WATCHLIST"),
                }
            ],
        )

        enable_dca = args.enable_dca1_sweep or os.getenv("HONGSTR_ENABLE_DCA1_SWEEP", "0").strip() in {"1", "true", "TRUE"}
        if enable_dca and not args.dry_run:
            dca_candidate = {
                "candidate_id": f"DCA1_{date_id}",
                "strategy_id": "dca1_supertrend",
                "family": "dca1",
                "symbol": proposal.symbol,
                "timeframe": proposal.timeframe,
                "direction": "LONG",
                "variant": "base_safety1",
                "parameters": {
                    "base_order": 1.0,
                    "safety_multiplier": 1.6,
                    "safety_gap_bps": 120.0,
                    "take_profit_pct": 1.1,
                    "stop_loss_pct": 2.3,
                    "trailing_pct": 0.7,
                },
            }
            sweep = run_dca1_sweep(
                dca_candidate,
                safety_multiplier_values=[1.4, 1.8],
                safety_gap_bps_values=[100.0, 180.0],
                fee_scenarios=("standard", "vip", "stress"),
                snapshot=snapshot,
            )
            dca_path = REPORTS_ROOT / datetime.now().strftime("%Y%m%d") / "dca1_sweep.json"
            dca_path.parent.mkdir(parents=True, exist_ok=True)
            dca_path.write_text(json.dumps(sweep, indent=2), encoding="utf-8")
            logger.info("DCA1 sweep artifact generated: %s (%s variants)", dca_path, len(sweep))

        # 7. Write enriched state
        write_state(
            status="OK" if not args.dry_run else "DRY_RUN",
            exp_id=proposal.experiment_id,
            gate_passed=gate_passed,
            report_path=str(report_path),
        )

        # 8. Telegram notify (non-blocking)
        notify_telegram(proposal, gate_passed, report_path, "OK" if not args.dry_run else "DRY_RUN")

        logger.info("Research Loop v2 completed successfully.")

    except Exception as e:
        logger.error(f"Research Loop failed: {e}", exc_info=True)
        try:
            write_state("WARN", error=str(e))
        except Exception:
            pass
        notify_telegram_warn(str(e))
        sys.exit(0)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
