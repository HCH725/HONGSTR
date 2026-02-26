from pathlib import Path
from typing import Any

def get_execution_quality_report(repo_path: Path, env: str) -> dict[str, Any]:
    """
    Execution Quality Report (Read-only).
    Currently a skeleton returning UNKNOWN as the SSOT does not exist.
    """
    ssot_path = repo_path / "data/state/execution_quality_latest.json"
    
    # Guidance on what's missing
    guidance = (
        "❌ Execution Quality SSOT missing.\n"
        "Expected file: `data/state/execution_quality_latest.json`.\n"
        "Please ensure the execution audit producer is integrated into `refresh_state.sh`."
    )

    return {
        "status": "UNKNOWN",
        "report_only": True,
        "markdown": f"📊 *Execution Quality Report*\n\n{guidance}",
        "data": {
            "error": "ssot_missing",
            "required_file": "data/state/execution_quality_latest.json",
            "env": env
        }
    }
