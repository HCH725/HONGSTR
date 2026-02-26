from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("research_gates")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "research/policy/overfit_gates_aggressive.json"

DEFAULT_POLICY: dict[str, Any] = {
    "name": "default_aggressive",
    "hard_gates": {
        "min_oos_sharpe": 0.5,
        "max_oos_mdd": -0.2,
        "min_trades_count": 10,
        "min_pnl_mult": 1.0,
        "max_is_oos_sharpe_ratio": 3.0,
    },
    "soft_targets": {
        "oos_sharpe": 1.0,
        "oos_mdd": -0.12,
        "trades_count": 30,
        "pnl_mult": 1.05,
        "total_cost_bps": 16.0,
    },
    "soft_weights": {
        "oos_sharpe": 20.0,
        "oos_mdd": 10.0,
        "trades_count": 5.0,
        "pnl_mult": 8.0,
        "total_cost_bps": 6.0,
    },
    "score": {
        "base": 100.0,
        "clip_min": 0.0,
        "clip_max": 180.0,
    },
}


@dataclass
class GateResult:
    passed: bool
    reason: str
    oos_sharpe: float
    oos_mdd: float
    details: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.passed

    def as_dict(self) -> dict[str, Any]:
        out = {
            "passed": bool(self.passed),
            "reason": str(self.reason),
            "oos_sharpe": float(self.oos_sharpe),
            "oos_mdd": float(self.oos_mdd),
        }
        out.update(self.details)
        return out


class ResearchGate:
    """
    Config-driven aggressive gate:
    - Hard gates decide PASS/FAIL.
    - Soft targets produce ranking score adjustment.
    - DRY_RUN always FAIL (report_only, non-blocking).
    """

    def __init__(self, policy_path: str | Path | None = None) -> None:
        env_override = os.getenv("HONGSTR_GATE_POLICY_PATH", "").strip()
        if policy_path is None and env_override:
            policy_path = env_override
        self.policy_path = Path(policy_path).resolve() if policy_path else DEFAULT_POLICY_PATH
        self.policy = _load_policy(self.policy_path)

    def evaluate(self, result: dict[str, Any]) -> bool:
        gate_result = self.evaluate_detailed(result)
        if gate_result.passed:
            logger.info("Research Gate: PASSED — %s", gate_result.reason)
        else:
            logger.warning("Research Gate: FAILED — %s", gate_result.reason)
        return gate_result.passed

    def evaluate_detailed(self, result: dict[str, Any]) -> GateResult:
        if str(result.get("status", "")).upper() == "DRY_RUN":
            return GateResult(
                passed=False,
                reason="DRY_RUN (not a real eval)",
                oos_sharpe=0.0,
                oos_mdd=0.0,
                details={
                    "policy_name": self.policy.get("name", "unknown"),
                    "hard_failures": ["dry_run"],
                    "soft_adjustments": {},
                    "final_score": 0.0,
                },
            )

        is_sharpe = _as_float(result.get("is_sharpe"), 0.0)
        oos_sharpe = _as_float(result.get("oos_sharpe"), 0.0)
        is_mdd = _as_float(result.get("is_mdd"), 0.0)
        oos_mdd = _as_float(result.get("oos_mdd"), 0.0)
        trades = _as_int(result.get("trades_count"), 0)
        pnl_mult = _as_float(result.get("pnl_mult"), 1.0)
        total_cost_bps = _as_float(result.get("total_cost_bps"), 0.0)

        hard = self.policy.get("hard_gates", {})
        soft_targets = self.policy.get("soft_targets", {})
        soft_weights = self.policy.get("soft_weights", {})
        score_cfg = self.policy.get("score", {})

        min_oos_sharpe = _as_float(hard.get("min_oos_sharpe"), 0.5)
        max_oos_mdd = _as_float(hard.get("max_oos_mdd"), -0.2)
        min_trades = _as_int(hard.get("min_trades_count"), 10)
        min_pnl = _as_float(hard.get("min_pnl_mult"), 1.0)
        max_ratio = _as_float(hard.get("max_is_oos_sharpe_ratio"), 3.0)

        hard_failures: list[str] = []
        if oos_sharpe < min_oos_sharpe:
            hard_failures.append(f"oos_sharpe {oos_sharpe:.4f} < {min_oos_sharpe:.4f}")
        if oos_mdd < max_oos_mdd:
            hard_failures.append(f"oos_mdd {oos_mdd:.4f} < {max_oos_mdd:.4f}")
        if trades < min_trades:
            hard_failures.append(f"trades_count {trades} < {min_trades}")
        if pnl_mult < min_pnl:
            hard_failures.append(f"pnl_mult {pnl_mult:.4f} < {min_pnl:.4f}")

        if is_sharpe > 0 and oos_sharpe > 0:
            ratio = is_sharpe / max(oos_sharpe, 1e-9)
            if ratio > max_ratio:
                hard_failures.append(f"is_oos_sharpe_ratio {ratio:.4f} > {max_ratio:.4f}")

        base = _as_float(score_cfg.get("base"), 100.0)
        clip_min = _as_float(score_cfg.get("clip_min"), 0.0)
        clip_max = _as_float(score_cfg.get("clip_max"), 180.0)
        score = base

        soft_adjustments: dict[str, float] = {}

        target_sharpe = _as_float(soft_targets.get("oos_sharpe"), 1.0)
        w_sharpe = _as_float(soft_weights.get("oos_sharpe"), 20.0)
        adj_sharpe = (oos_sharpe - target_sharpe) * w_sharpe
        soft_adjustments["oos_sharpe"] = round(adj_sharpe, 6)
        score += adj_sharpe

        target_mdd = _as_float(soft_targets.get("oos_mdd"), -0.12)
        w_mdd = _as_float(soft_weights.get("oos_mdd"), 10.0)
        adj_mdd = (oos_mdd - target_mdd) * 100.0 * w_mdd
        soft_adjustments["oos_mdd"] = round(adj_mdd, 6)
        score += adj_mdd

        target_trades = max(1, _as_int(soft_targets.get("trades_count"), 30))
        w_trades = _as_float(soft_weights.get("trades_count"), 5.0)
        adj_trades = ((trades - target_trades) / float(target_trades)) * w_trades
        soft_adjustments["trades_count"] = round(adj_trades, 6)
        score += adj_trades

        target_pnl = _as_float(soft_targets.get("pnl_mult"), 1.05)
        w_pnl = _as_float(soft_weights.get("pnl_mult"), 8.0)
        adj_pnl = (pnl_mult - target_pnl) * 100.0 * w_pnl
        soft_adjustments["pnl_mult"] = round(adj_pnl, 6)
        score += adj_pnl

        target_cost = _as_float(soft_targets.get("total_cost_bps"), 16.0)
        w_cost = _as_float(soft_weights.get("total_cost_bps"), 6.0)
        adj_cost = (target_cost - total_cost_bps) * (w_cost / 4.0)
        soft_adjustments["total_cost_bps"] = round(adj_cost, 6)
        score += adj_cost

        score = max(clip_min, min(clip_max, score))

        passed = len(hard_failures) == 0
        reason = "All hard gates passed" if passed else "; ".join(hard_failures)

        return GateResult(
            passed=passed,
            reason=reason,
            oos_sharpe=oos_sharpe,
            oos_mdd=oos_mdd,
            details={
                "policy_name": self.policy.get("name", "unknown"),
                "hard_failures": hard_failures,
                "soft_adjustments": soft_adjustments,
                "final_score": round(score, 6),
                "metrics": {
                    "is_sharpe": is_sharpe,
                    "oos_sharpe": oos_sharpe,
                    "is_mdd": is_mdd,
                    "oos_mdd": oos_mdd,
                    "trades_count": trades,
                    "pnl_mult": pnl_mult,
                    "total_cost_bps": total_cost_bps,
                },
            },
        )


def _load_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        logger.warning("Policy not found (%s), using defaults.", path)
        return dict(DEFAULT_POLICY)

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Policy parse failed (%s): %s. Using defaults.", path, exc)
        return dict(DEFAULT_POLICY)

    if not isinstance(obj, dict):
        logger.warning("Policy invalid type (%s), using defaults.", path)
        return dict(DEFAULT_POLICY)

    merged = dict(DEFAULT_POLICY)
    for key in ("hard_gates", "soft_targets", "soft_weights", "score"):
        base = dict(DEFAULT_POLICY.get(key, {}))
        incoming = obj.get(key, {})
        if isinstance(incoming, dict):
            base.update(incoming)
        merged[key] = base
    if isinstance(obj.get("name"), str) and obj.get("name"):
        merged["name"] = obj["name"]
    return merged


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)
