import pandas as pd

def make_labels(panel: pd.DataFrame) -> pd.DataFrame:
    """Stub for creating classification/regression labels (targets) from the panel."""
    # MVP: Not currently used. Will return an empty dataframe aligned to the panel.
    return pd.DataFrame(index=panel.index)
