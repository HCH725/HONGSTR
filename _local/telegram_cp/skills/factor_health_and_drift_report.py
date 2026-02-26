from pathlib import Path
from typing import Any

from research.loop.specialist_skill_skeletons import (
    factor_health_and_drift_report as _factor_health_and_drift_report,
)


def get_factor_health_report(repo_path: Path, factor_id: str) -> dict[str, Any]:
    """tg_cp proxy for report-only quant skeleton B2."""
    payload = _factor_health_and_drift_report(
        repo_path,
        factor_name=factor_id,
    )
    inputs = payload.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs["factor_id"] = factor_id
    return payload
