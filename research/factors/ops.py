import pandas as pd
import numpy as np

def returns_1(s: pd.Series, shift: int = 1) -> pd.Series:
    """Computes simple 1-period return, lagged by `shift` periods to avoid lookahead."""
    return s.pct_change(1).shift(shift)

def ema_diff(s: pd.Series, fast: int, slow: int, shift: int = 1) -> pd.Series:
    """Computes EMA(fast) - EMA(slow) scaled by EMA(slow), lagged by `shift`."""
    fast_ema = s.ewm(span=fast, adjust=False).mean()
    slow_ema = s.ewm(span=slow, adjust=False).mean()
    diff = (fast_ema - slow_ema) / slow_ema
    return diff.shift(shift)

def atr_n(high: pd.Series, low: pd.Series, close: pd.Series, n: int, shift: int = 1) -> pd.Series:
    """Computes Average True Range over `n` periods, lagged by `shift`."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # Simple moving average of TR for ATR as a baseline
    atr = tr.rolling(window=n).mean()
    return atr.shift(shift)

def vola_n(s: pd.Series, n: int, shift: int = 1) -> pd.Series:
    """Computes rolling standard deviation over `n` periods, lagged by `shift`."""
    return s.rolling(window=n).std().shift(shift)

def breakout_n(s: pd.Series, n: int, type: str = 'high', shift: int = 1) -> pd.Series:
    """Computes distance to n-period rolling High or Low, lagged by `shift`."""
    if type == 'high':
        rolling_extreme = s.rolling(window=n).max()
    else:
        rolling_extreme = s.rolling(window=n).min()
    
    dist = (s - rolling_extreme) / s
    return dist.shift(shift)
