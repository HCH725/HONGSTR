from pathlib import Path
from typing import Any

from research.loop.report_only_research_skills import (
    data_lineage_fingerprint as _data_lineage_fingerprint,
)


def get_data_lineage_fingerprint(repo_path: Path) -> dict[str, Any]:
    """tg_cp proxy for a read-only lineage fingerprint preview."""
    return _data_lineage_fingerprint(repo_path, write_artifacts=False)
