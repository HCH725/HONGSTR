from pathlib import Path
from typing import Any

from research.loop.specialist_skill_skeletons import (
    strategy_regime_sensitivity_report as _strategy_regime_sensitivity_report,
)


def get_strategy_sensitivity_report(repo_path: Path, strategy_id: str) -> dict[str, Any]:
    """tg_cp proxy for report-only quant skeleton B5."""
    payload = _strategy_regime_sensitivity_report(
        repo_path,
        strategy_id=strategy_id,
    )
    inputs = payload.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs["strategy_id"] = strategy_id
    return payload
