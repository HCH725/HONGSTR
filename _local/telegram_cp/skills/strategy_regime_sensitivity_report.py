import json
from pathlib import Path
from typing import Any

def get_strategy_sensitivity_report(repo_path: Path, strategy_id: str) -> dict[str, Any]:
    """
    SKELETON: Strategy Regime Sensitivity Report.
    """
    research_dir = repo_path / "reports/research/sensitivity"
    found_artifact = research_dir / f"sensitivity_{strategy_id}.json"
    
    if not found_artifact.exists():
        return {
            "status": "UNKNOWN",
            "report_only": True,
            "markdown": f"🧩 *Strategy Sensitivity Report*\n\n❌ Artifact missing for `{strategy_id}`.\nExpected: `reports/research/sensitivity/sensitivity_{strategy_id}.json`.",
            "data": {"error": "artifact_missing", "strategy_id": strategy_id}
        }

    try:
        with open(found_artifact, "r") as f:
            data = json.load(f)
            return {
                "status": "OK",
                "report_only": True,
                "markdown": f"🧩 *Strategy Sensitivity Report*\n\n✅ Found sensitivity report for `{strategy_id}`.",
                "data": data
            }
    except Exception as e:
        return {
            "status": "UNKNOWN",
            "report_only": True,
            "markdown": f"🧩 *Strategy Sensitivity Report*\n\n❌ Error reading artifact: {e}",
            "data": {"error": str(e)}
        }
