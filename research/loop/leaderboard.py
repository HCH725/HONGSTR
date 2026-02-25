"""
HONGSTR Research Leaderboard
Ranks all completed experiments by OOS Sharpe (descending).
Reads from reports/research/ and writes to data/state/_research/leaderboard.json.
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_ROOT = REPO_ROOT / "reports/research"
LEADERBOARD_PATH = REPO_ROOT / "data/state/_research/leaderboard.json"

logger = logging.getLogger("research_leaderboard")


def build_leaderboard(top_n: int = 10) -> List[Dict[str, Any]]:
    """
    Scan all *_results.json files under reports/research/,
    filter those with gate status, rank by oos_sharpe DESC.
    """
    entries = []
    if not REPORTS_ROOT.exists():
        return entries

    for results_file in sorted(REPORTS_ROOT.rglob("*_results.json")):
        try:
            data = json.loads(results_file.read_text())
            # Require at minimum oos_sharpe to be rankable
            if "oos_sharpe" not in data:
                continue
            exp_id_stem = results_file.stem.replace("_results", "")
            entry = {
                "experiment_id": data.get("experiment_id", exp_id_stem),
                "oos_sharpe": data.get("oos_sharpe", 0.0),
                "oos_mdd": data.get("oos_mdd", 0.0),
                "is_sharpe": data.get("is_sharpe", 0.0),
                "timestamp": data.get("timestamp", ""),
                "status": data.get("status", "UNKNOWN"),
                "report_dir": str(results_file.parent),
            }
            entries.append(entry)
        except Exception as e:
            logger.warning(f"Could not parse {results_file}: {e}")

    # Rank by OOS Sharpe descending (stability-first: OOS is the only axis)
    ranked = sorted(entries, key=lambda x: x["oos_sharpe"], reverse=True)
    return ranked[:top_n]


def save_leaderboard(top_n: int = 10) -> Path:
    """Build and persist the leaderboard. Returns path written."""
    board = build_leaderboard(top_n=top_n)
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "ranked_by": "oos_sharpe_desc",
        "top_n": top_n,
        "entries": board,
    }
    LEADERBOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEADERBOARD_PATH.write_text(json.dumps(payload, indent=2))
    logger.info(f"Leaderboard saved: {len(board)} entries → {LEADERBOARD_PATH}")
    return LEADERBOARD_PATH


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    path = save_leaderboard()
    print(f"Leaderboard written to {path}")
    board = json.loads(path.read_text())
    for i, e in enumerate(board.get("entries", []), 1):
        print(f"#{i} {e['experiment_id']} OOS_Sharpe={e['oos_sharpe']:.2f} OOS_MDD={e['oos_mdd']:.2%}")
    sys.exit(0)
