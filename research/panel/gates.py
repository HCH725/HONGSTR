import logging
import pandas as pd

logger = logging.getLogger("research.gates")

def gate_unique_key(panel: pd.DataFrame) -> bool:
    """Verifies that the index (ts, symbol) is strictly unique."""
    if panel.index.has_duplicates:
        logger.warning(f"[GATE FAILED] gate_unique_key: Panel has {panel.index.duplicated().sum()} duplicated index keys.")
        return False
    return True

def gate_sorted(panel: pd.DataFrame) -> bool:
    """Verifies that the multi-index is monotonically increasing (sorted)."""
    if not panel.index.is_monotonic_increasing:
        logger.warning("[GATE FAILED] gate_sorted: Panel index is not monotonically increasing (not sorted).")
        return False
    return True

def gate_coverage(panel: pd.DataFrame, max_gap_ratio: float = 0.05, max_missing_ratio: float = 0.05) -> bool:
    """
    Verifies data coverage and continuity.
    Missing raw OHLCV prices trigger warnings if they exceed the allowable ratio.
    """
    # Simply check missing data on core OHLCV columns
    core_cols = ["open", "high", "low", "close", "volume"]
    missing = [c for c in core_cols if c not in panel.columns]
    if missing:
        logger.warning(f"[GATE FAILED] gate_coverage: Missing core columns {missing}.")
        return False

    total_rows = len(panel)
    if total_rows == 0:
        logger.warning("[GATE FAILED] gate_coverage: Panel is empty.")
        return False

    null_counts = panel[core_cols].isnull().sum()
    max_nulls = null_counts.max()
    missing_ratio = max_nulls / total_rows

    if missing_ratio > max_missing_ratio:
        logger.warning(f"[GATE FAILED] gate_coverage: Missing ratio {missing_ratio:.4f} > {max_missing_ratio}.")
        return False

    # Gap ratio (e.g., sequential gaps in timestamps per symbol) could be complex,
    # keeping it simple for MVP by just relying on missing_ratio
    return True

def run_all_gates(panel: pd.DataFrame) -> bool:
    """Run all quality gates and return True if all passed. Failures print warnings but do not raise Exceptions."""
    a = gate_unique_key(panel)
    b = gate_sorted(panel)
    c = gate_coverage(panel)
    return a and b and c
