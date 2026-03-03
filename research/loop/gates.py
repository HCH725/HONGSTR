from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("research_gates")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "research/policy/overfit_gates_aggressive.json"

DEFAULT_POLICY: dict[str, Any] = {
    "name": "aggressive_yield_first_default",
    "hard_gates": {
        "min_oos_sharpe": 0.5,
        "max_oos_mdd": -0.2,
        "min_trades_count": 10,
        "min_pnl_mult": 1.0,
        "max_is_oos_sharpe_ratio": 3.0,
    },
    "soft_targets": {
        "oos_sharpe": 0.9,
        "oos_mdd": -0.12,
        "trades_count": 30,
        "pnl_mult": 1.05,
    },
    "soft_penalties": {
        "oos_sharpe_below_target": 12.0,
        "oos_mdd_worse_target": 10.0,
        "trades_shortfall": 5.0,
        "pnl_shortfall": 8.0,
    },
    "score": {
        "base": 100.0,
        "clip_min": 0.0,
        "clip_max": 160.0,
        "hard_fail_penalty": 40.0,
    },
    "watchlist": {
        "min_candidates": 1,
        "recommend_if_score_ge": 55.0,
    },
}


@dataclass
class GateResult:
    passed: bool
    reason: str
    oos_sharpe: float
    oos_mdd: float
    final_score: float
    recommendation: str
    hard_failures: list[str]
    soft_penalties: dict[str, float]
    policy_name: str

    def __bool__(self) -> bool:
        return self.passed

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "oos_sharpe": self.oos_sharpe,
            "oos_mdd": self.oos_mdd,
            "final_score": self.final_score,
            "recommendation": self.recommendation,
            "hard_failures": list(self.hard_failures),
            "soft_penalties": dict(self.soft_penalties),
            "policy_name": self.policy_name,
        }


class ResearchGate:
    """Config-driven aggressive gate with hard+soft tiers and watchlist recommendation."""

    def __init__(self, policy_path: str | Path | None = None):
        self.policy_path = Path(policy_path).resolve() if policy_path else DEFAULT_POLICY_PATH
        self.policy = _load_policy(self.policy_path)

    def evaluate(self, result: dict[str, Any]) -> bool:
        gate_result = self.evaluate_detailed(result)
        if gate_result.passed:
            logger.info("Research Gate: PASSED - %s (score=%.2f)", gate_result.reason, gate_result.final_score)
        else:
            logger.warning("Research Gate: FAILED - %s (score=%.2f)", gate_result.reason, gate_result.final_score)
        return gate_result.passed

    def evaluate_detailed(self, result: dict[str, Any]) -> GateResult:
        if result.get("status") == "DRY_RUN":
            return GateResult(
                passed=False,
                reason="DRY_RUN (not a real eval)",
                oos_sharpe=0.0,
                oos_mdd=0.0,
                final_score=0.0,
                recommendation="WATCHLIST",
                hard_failures=["dry_run"],
                soft_penalties={},
                policy_name=str(self.policy.get("name", "unknown")),
            )

        hard_cfg = self.policy.get("hard_gates", {})
        soft_cfg = self.policy.get("soft_targets", {})
        pen_cfg = self.policy.get("soft_penalties", {})
        score_cfg = self.policy.get("score", {})
        watch_cfg = self.policy.get("watchlist", {})

        is_sharpe = _as_float(result.get("is_sharpe"), 0.0)
        oos_sharpe = _as_float(result.get("oos_sharpe"), 0.0)
        oos_mdd = _as_float(result.get("oos_mdd"), 0.0)
        trades_count = _as_int(result.get("trades_count"), 0)
        pnl_mult = _as_float(result.get("pnl_mult"), 1.0)

        hard_failures: list[str] = []
        if oos_sharpe < _as_float(hard_cfg.get("min_oos_sharpe"), 0.5):
            hard_failures.append("oos_sharpe_below_floor")
        if oos_mdd < _as_float(hard_cfg.get("max_oos_mdd"), -0.2):
            hard_failures.append("oos_mdd_worse_than_ceiling")
        if trades_count < _as_int(hard_cfg.get("min_trades_count"), 10):
            hard_failures.append("trades_below_min")
        if pnl_mult < _as_float(hard_cfg.get("min_pnl_mult"), 1.0):
            hard_failures.append("pnl_below_min")

        max_ratio = _as_float(hard_cfg.get("max_is_oos_sharpe_ratio"), 3.0)
        if oos_sharpe > 0:
            ratio = is_sharpe / oos_sharpe
            if ratio > max_ratio:
                hard_failures.append("is_oos_sharpe_ratio_too_high")

        soft_penalties: dict[str, float] = {}
        penalty_total = 0.0

        target_sharpe = _as_float(soft_cfg.get("oos_sharpe"), 0.9)
        if oos_sharpe < target_sharpe:
            penalty = (target_sharpe - oos_sharpe) * _as_float(pen_cfg.get("oos_sharpe_below_target"), 12.0)
            soft_penalties["oos_sharpe"] = round(penalty, 6)
            penalty_total += penalty

        target_mdd = _as_float(soft_cfg.get("oos_mdd"), -0.12)
        if oos_mdd < target_mdd:
            penalty = abs(target_mdd - oos_mdd) * 100.0 * _as_float(pen_cfg.get("oos_mdd_worse_target"), 10.0)
            soft_penalties["oos_mdd"] = round(penalty, 6)
            penalty_total += penalty

        target_trades = max(1, _as_int(soft_cfg.get("trades_count"), 30))
        if trades_count < target_trades:
            shortfall = (target_trades - trades_count) / target_trades
            penalty = shortfall * _as_float(pen_cfg.get("trades_shortfall"), 5.0)
            soft_penalties["trades_count"] = round(penalty, 6)
            penalty_total += penalty

        target_pnl = _as_float(soft_cfg.get("pnl_mult"), 1.05)
        if pnl_mult < target_pnl:
            penalty = (target_pnl - pnl_mult) * 100.0 * _as_float(pen_cfg.get("pnl_shortfall"), 8.0)
            soft_penalties["pnl_mult"] = round(penalty, 6)
            penalty_total += penalty

        score = _as_float(score_cfg.get("base"), 100.0)
        score -= penalty_total
        if hard_failures:
            score -= _as_float(score_cfg.get("hard_fail_penalty"), 40.0)
        score = max(_as_float(score_cfg.get("clip_min"), 0.0), min(_as_float(score_cfg.get("clip_max"), 160.0), score))

        passed = len(hard_failures) == 0
        if passed:
            recommendation = "PROMOTE"
        elif score >= _as_float(watch_cfg.get("recommend_if_score_ge"), 55.0):
            recommendation = "WATCHLIST"
        else:
            recommendation = "DEMOTE"

        reason = "All hard gates passed" if passed else ",".join(hard_failures)
        return GateResult(
            passed=passed,
            reason=reason,
            oos_sharpe=oos_sharpe,
            oos_mdd=oos_mdd,
            final_score=round(score, 6),
            recommendation=recommendation,
            hard_failures=hard_failures,
            soft_penalties=soft_penalties,
            policy_name=str(self.policy.get("name", "unknown")),
        )

    def apply_watchlist_floor(self, ranked_candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ensure candidate list never goes empty under strict hard-gate failures."""
        floor = max(1, _as_int(self.policy.get("watchlist", {}).get("min_candidates"), 1))
        if not ranked_candidates:
            return ranked_candidates

        promoted = [c for c in ranked_candidates if str(c.get("recommendation", "")).upper() == "PROMOTE"]
        if promoted:
            return ranked_candidates

        watchlist = [c for c in ranked_candidates if str(c.get("recommendation", "")).upper() == "WATCHLIST"]
        if len(watchlist) >= floor:
            return ranked_candidates

        sorted_candidates = sorted(ranked_candidates, key=lambda x: float(x.get("final_score", 0.0)), reverse=True)
        injected = 0
        for cand in sorted_candidates:
            if str(cand.get("recommendation", "")).upper() == "WATCHLIST":
                continue
            cand["recommendation"] = "WATCHLIST"
            cand["watchlist_floor_injected"] = True
            injected += 1
            if len(watchlist) + injected >= floor:
                break
        return sorted_candidates


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Gate policy missing (%s); using defaults", path)
        return DEFAULT_POLICY
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Gate policy unreadable (%s): %s; using defaults", path, exc)
        return DEFAULT_POLICY
    if not isinstance(obj, dict):
        logger.warning("Gate policy invalid type (%s); using defaults", path)
        return DEFAULT_POLICY

    merged = dict(DEFAULT_POLICY)
    for key in ("hard_gates", "soft_targets", "soft_penalties", "score", "watchlist"):
        base = dict(DEFAULT_POLICY.get(key, {}))
        incoming = obj.get(key, {})
        if isinstance(incoming, dict):
            base.update(incoming)
        merged[key] = base
    if isinstance(obj.get("name"), str) and obj.get("name"):
        merged["name"] = obj["name"]
    return merged


def _as_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _as_int(v: Any, default: int) -> int:
    try:
        return int(v)
    except Exception:
        return int(default)
