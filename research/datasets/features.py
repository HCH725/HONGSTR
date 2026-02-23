import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import hashlib

from research.factors.registry import FactorRegistry

logger = logging.getLogger("research.datasets")

def get_git_commit() -> str:
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    except Exception:
        return "unknown"

def make_features(panel: pd.DataFrame, set_name: str, strict_index: bool = True) -> pd.DataFrame:
    """
    Applies pure factor definitions from FactorRegistry onto the panel.
    Returns a new DataFrame with just the computed features (plus the same index).
    """
    if len(panel) == 0:
        logger.warning(f"make_features called with empty panel for set {set_name}.")
        return pd.DataFrame(index=panel.index)

    # Need symbols to do grouped operations
    # Assuming multi-index ['ts', 'symbol']
    if "symbol" not in panel.index.names:
        logger.error("Panel does not have 'symbol' in index. Cannot apply grouped factors safely.")
        return pd.DataFrame()

    factors = FactorRegistry.get_set(set_name)
    results = {}

    for fdef in factors:
        missing = [c for c in fdef.required_cols if c not in panel.columns]
        if missing:
            logger.warning(f"Factor {fdef.name} missing req cols: {missing}. Filling NaN.")
            results[fdef.name] = pd.Series(index=panel.index, dtype=float)
            continue
            
        try:
            # Apply function grouped by symbol
            res_series = panel.groupby("symbol", group_keys=False).apply(fdef.func)
            results[fdef.name] = res_series
        except Exception as e:
            logger.warning(f"Factor {fdef.name} failed to compute: {e}. Filling NaN.")
            results[fdef.name] = pd.Series(index=panel.index, dtype=float)

    feat_df = pd.DataFrame(results, index=panel.index)

    if strict_index:
        if not feat_df.index.equals(panel.index):
            logger.warning("[STRICT_INDEX] make_features produced an index that does not match the input panel exactly.")

    return feat_df

def save_manifest(out_dir: str, freq: str, rowcount: int, file_hash: str):
    """Saves manifest.json alongside the features parquet files."""
    out_path = Path(out_dir)
    manifest_file = out_path / "manifest.json"
    
    entry = {
        "freq": freq,
        "rowcount": rowcount,
        "hash": file_hash,
        "git_commit": get_git_commit(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Load existing manifest or start fresh
    if manifest_file.exists():
        try:
            with open(manifest_file, "r") as f:
                data = json.load(f)
        except Exception:
            data = {"runs": []}
    else:
        data = {"runs": []}
        
    data["runs"].append(entry)
    
    with open(manifest_file, "w") as f:
        json.dump(data, f, indent=2)

def compute_hash(file_path: Path) -> str:
    """Computes SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for b in iter(lambda: f.read(4096), b""):
                sha256.update(b)
        return sha256.hexdigest()
    except Exception:
        return "hash_error"
