from pathlib import Path
from typing import Any

from research.loop.report_only_research_skills import (
    backtest_repro_gate as _backtest_repro_gate,
)


def get_backtest_repro_gate(
    repo_path: Path,
    candidate_id: str,
    slice_ref: str = "",
    code_ref: str = "",
    runs: int = 3,
) -> dict[str, Any]:
    """tg_cp proxy for a read-only repro gate preview."""
    return _backtest_repro_gate(
        repo_path,
        candidate_id=candidate_id,
        slice_ref=slice_ref,
        code_ref=code_ref,
        runs=runs,
        write_artifacts=False,
    )
