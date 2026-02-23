import pandas as pd
import logging

logger = logging.getLogger("research.labels")

def make_labels(panel: pd.DataFrame, horizon_bars: int) -> pd.DataFrame:
    """
    Creates classification and regression labels from a panel.
    Strictly avoids look-ahead by using shift(-horizon) grouped by symbol.
    """
    if "close" not in panel.columns:
        logger.error("make_labels requires 'close' column in the panel.")
        return pd.DataFrame(index=panel.index)

    if "symbol" not in panel.index.names:
        logger.error("make_labels requires 'symbol' in the index.")
        return pd.DataFrame(index=panel.index)

    def _compute_target(df: pd.DataFrame):
        # fwd_return measures return from "current close" to "future close at horizon"
        # Since it's a forward return, we shift BACKWARDS (-horizon) so that the current index
        # aligns with what the price will be in the future.
        future_close = df["close"].shift(-horizon_bars)
        fwd_ret = (future_close - df["close"]) / df["close"]
        
        return pd.DataFrame({
            "fwd_return": fwd_ret,
            "direction": (fwd_ret > 0).astype(float).where(fwd_ret.notnull())
        }, index=df.index)

    labels = panel.groupby("symbol", group_keys=False).apply(_compute_target)
    
    return labels
