import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger("research.datasets.assembly")

def check_leakage(columns) -> bool:
    bad_keywords = ["future", "next", "target", "label", "forward"]
    for c in columns:
        c_lower = str(c).lower()
        if any(b in c_lower for b in bad_keywords):
            return False
    return True

def build_ml_dataset(features_path: Path, labels_path: Path, drop_nan=True) -> pd.DataFrame:
    """
    Merges Features (X) and Labels (y) strictly on the (ts, symbol) MultiIndex.
    """
    if not features_path.exists():
        logger.error(f"Features file not found: {features_path}")
        return pd.DataFrame()
        
    if not labels_path.exists():
        logger.error(f"Labels file not found: {labels_path}")
        return pd.DataFrame()

    features_df = pd.read_parquet(features_path)
    labels_df = pd.read_parquet(labels_path)
    
    # Validation 1: Exact index match
    if not features_df.index.equals(labels_df.index):
        logger.warning("Dataset Builder Gate Failed: Features index and Labels index DO NOT match exactly.")
        # Proceed with inner join as fallback
        dataset = features_df.join(labels_df, how="inner")
        logger.info(f"Inner join fallback resulted in {len(dataset)} rows.")
    else:
        dataset = pd.concat([features_df, labels_df], axis=1)
        
    # Validation 2: Leakage check on X
    if not check_leakage(features_df.columns):
        logger.warning("Dataset Builder Gate Failed: Leakage keywords suspected in feature columns.")

    if drop_nan:
        before = len(dataset)
        dataset = dataset.dropna()
        after = len(dataset)
        logger.info(f"Dropped {before - after} rows with NaN (expected for window factors + future labels). Data remaining: {after}")

    return dataset
