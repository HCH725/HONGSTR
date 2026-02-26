from pathlib import Path
from typing import Any

from research.loop.specialist_skill_skeletons import (
    backtest_reproducibility_audit as _backtest_reproducibility_audit,
)


def audit_backtest_reproducibility(repo_path: Path, backtest_id: str, baseline_sha: str) -> dict[str, Any]:
    """tg_cp proxy for report-only quant skeleton B1."""
    payload = _backtest_reproducibility_audit(
        repo_path,
        split_ref=baseline_sha,
        run_id=backtest_id,
    )
    inputs = payload.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs["backtest_id"] = backtest_id
        inputs["baseline_sha"] = baseline_sha
    return payload
