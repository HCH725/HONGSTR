import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("research_gates")

# Overfit detection: reject if IS sharpe is more than OVERFIT_RATIO × OOS sharpe
OVERFIT_RATIO = 2.0


class GateResult:
    """Structured result from gate evaluation."""
    def __init__(self, passed: bool, reason: str, oos_sharpe: float, oos_mdd: float):
        self.passed = passed
        self.reason = reason
        self.oos_sharpe = oos_sharpe
        self.oos_mdd = oos_mdd

    def __bool__(self):
        return self.passed

    def as_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "reason": self.reason,
            "oos_sharpe": self.oos_sharpe,
            "oos_mdd": self.oos_mdd,
        }


class ResearchGate:
    """
    OOS/WF priority gate for research experiments.
    - IS metrics are RECORDED but never used to pass the gate.
    - Overfit detection: reject if IS sharpe >> OOS sharpe by OVERFIT_RATIO.
    - DRY_RUN results auto-fail (gate_passed=False), not WARN.
    """
    def __init__(
        self,
        min_oos_sharpe: float = 0.5,
        max_oos_mdd: float = -0.15,
        overfit_ratio: float = OVERFIT_RATIO,
    ):
        self.min_oos_sharpe = min_oos_sharpe
        self.max_oos_mdd = max_oos_mdd
        self.overfit_ratio = overfit_ratio

    def evaluate(self, result: Dict[str, Any]) -> bool:
        """
        Evaluate a backtest result. Returns True if PASSED, False otherwise.
        Logs the gate_reason for auditability.
        """
        gate_result = self.evaluate_detailed(result)
        if gate_result.passed:
            logger.info(f"Research Gate: PASSED — {gate_result.reason}")
        else:
            logger.warning(f"Research Gate: FAILED — {gate_result.reason}")
        return gate_result.passed

    def evaluate_detailed(self, result: Dict[str, Any]) -> GateResult:
        """Full evaluation returning a GateResult with structured reason."""
        # DRY_RUN is always a non-gate-fail (informational)
        if result.get("status") == "DRY_RUN":
            return GateResult(False, "DRY_RUN (not a real eval)", 0.0, 0.0)

        is_sharpe = result.get("is_sharpe", 0.0)
        oos_sharpe = result.get("oos_sharpe", 0.0)
        oos_mdd = result.get("oos_mdd", 0.0)

        logger.info(
            f"Gate Eval: IS_Sharpe={is_sharpe:.2f}, OOS_Sharpe={oos_sharpe:.2f}, OOS_MDD={oos_mdd:.2%}"
        )

        # 1. OOS Sharpe floor
        if oos_sharpe < self.min_oos_sharpe:
            return GateResult(
                False,
                f"OOS Sharpe {oos_sharpe:.2f} below threshold {self.min_oos_sharpe}",
                oos_sharpe, oos_mdd,
            )

        # 2. OOS MDD ceiling
        if oos_mdd < self.max_oos_mdd:
            return GateResult(
                False,
                f"OOS MDD {oos_mdd:.2%} exceeds threshold {self.max_oos_mdd:.2%}",
                oos_sharpe, oos_mdd,
            )

        # 3. Overfit detection (IS >> OOS)
        if is_sharpe > 0 and oos_sharpe > 0 and (is_sharpe / oos_sharpe) > self.overfit_ratio:
            return GateResult(
                False,
                f"Overfit detected: IS_Sharpe/OOS_Sharpe={is_sharpe/oos_sharpe:.1f}x > {self.overfit_ratio}x",
                oos_sharpe, oos_mdd,
            )

        return GateResult(True, "All OOS/WF checks passed", oos_sharpe, oos_mdd)
