import pandas as pd
import numpy as np

class RegimeLabeler:
    """
    Deterministic Regime Labeling (Phase 0).
    Based on 4h EMA50 / EMA200 relationship with hysteresis.
    """
    def __init__(self, hysteresis: float = 0.003):
        self.hysteresis = hysteresis

    def label_regime(self, df_4h: pd.DataFrame) -> pd.Series:
        """
        Input: DataFrame with 'close'.
        Output: Series with 'BULL', 'BEAR', 'NEUTRAL'.
        """
        df = df_4h.copy()
        if 'close' not in df.columns:
            return pd.Series(index=df.index, data='NEUTRAL')
            
        # Compute EMAs
        ema50 = df['close'].ewm(span=50, adjust=False).mean()
        ema200 = df['close'].ewm(span=200, adjust=False).mean()
        
        # Logic
        # Bull: Close > EMA200 * (1+z) AND EMA50 > EMA200
        # Bear: Close < EMA200 * (1-z) AND EMA50 < EMA200
        # Else: Neutral
        
        z = self.hysteresis
        
        conditions = [
            (df['close'] > ema200 * (1 + z)) & (ema50 > ema200),
            (df['close'] < ema200 * (1 - z)) & (ema50 < ema200)
        ]
        choices = ['BULL', 'BEAR']
        
        return pd.Series(np.select(conditions, choices, default='NEUTRAL'), index=df.index)
