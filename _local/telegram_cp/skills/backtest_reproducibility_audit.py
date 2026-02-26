from pathlib import Path
from typing import Any

from research.loop.specialist_skill_skeletons import (
    backtest_reproducibility_audit as _backtest_reproducibility_audit,
)


def audit_backtest_reproducibility(
    repo_path: Path,
    backtest_id: str = "",
    baseline_sha: str = "",
    *,
    strategy_id: str = "",
    runs: int = 1,
    report_only: bool = True,
    manifest_path: str = "reports/research/backtest_manifest.json",
) -> dict[str, Any]:
    """tg_cp proxy for report-only quant skeleton B1."""
    run_id = strategy_id or backtest_id
    split_ref = baseline_sha or f"runs={int(runs)}"
    payload = _backtest_reproducibility_audit(
        repo_path,
        manifest_path=manifest_path,
        split_ref=split_ref,
        run_id=run_id,
    )
    inputs = payload.setdefault("inputs", {})
    if isinstance(inputs, dict):
        inputs["strategy_id"] = strategy_id
        inputs["runs"] = int(runs)
        inputs["report_only"] = bool(report_only)
        inputs["backtest_id"] = backtest_id
        inputs["baseline_sha"] = baseline_sha
        inputs["manifest_path"] = manifest_path
    return payload
