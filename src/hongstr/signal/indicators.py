import pandas as pd
import numpy as np
from typing import Tuple, List

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.rolling(window=period).mean() # Simple moving average of TR
    # Alternatively use EMA for ATR: tr.ewm(alpha=1/period, adjust=False).mean()

def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Returns (trend_direction, supertrend_band)
    trend_direction: 1 for LONG (bullish), -1 for SHORT (bearish)
    """
    hl2 = (high + low) / 2
    my_atr = atr(high, low, close, period)
    
    upperband = hl2 + (multiplier * my_atr)
    lowerband = hl2 - (multiplier * my_atr)
    
    # Initialize result series
    trend = pd.Series(index=close.index, dtype=float).fillna(0)
    final_upper = pd.Series(index=close.index, dtype=float).fillna(0)
    final_lower = pd.Series(index=close.index, dtype=float).fillna(0)
    st = pd.Series(index=close.index, dtype=float).fillna(0)
    
    # Iterative calculation (Supertrend is recursive)
    # We can optimize this with numpy for speed, but loop is clearer for correctness first.
    # Assuming pre-filled with NaNs or 0s.
    
    # Convert to numpy for performance
    c_arr = close.values
    ub_arr = upperband.values
    lb_arr = lowerband.values
    
    f_ub = np.zeros(len(c_arr))
    f_lb = np.zeros(len(c_arr))
    dir_arr = np.zeros(len(c_arr))
    st_arr = np.zeros(len(c_arr))
    
    for i in range(1, len(c_arr)):
        if np.isnan(c_arr[i]) or np.isnan(ub_arr[i]) or np.isnan(lb_arr[i]):
            continue
            
        # Upper Band Logic
        if ub_arr[i] < f_ub[i-1] or c_arr[i-1] > f_ub[i-1]:
            f_ub[i] = ub_arr[i]
        else:
            f_ub[i] = f_ub[i-1]
            
        # Lower Band Logic
        if lb_arr[i] > f_lb[i-1] or c_arr[i-1] < f_lb[i-1]:
            f_lb[i] = lb_arr[i]
        else:
            f_lb[i] = f_lb[i-1]
            
        # Trend Logic
        # prev trend
        prev_dir = dir_arr[i-1]
        
        if prev_dir == 1:
            if c_arr[i] < f_lb[i]:
                dir_arr[i] = -1
            else:
                dir_arr[i] = 1
        elif prev_dir == -1:
            if c_arr[i] > f_ub[i]:
                dir_arr[i] = 1
            else:
                dir_arr[i] = -1
        else:
            # Init trend (first valid bar)
            if c_arr[i] > c_arr[i-1]: # Simple init
                dir_arr[i] = 1
            else:
                dir_arr[i] = -1
                
        if dir_arr[i] == 1:
            st_arr[i] = f_lb[i]
        else:
            st_arr[i] = f_ub[i]
            
    return pd.Series(dir_arr, index=close.index), pd.Series(st_arr, index=close.index)

def vwap_session(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, times: pd.Series) -> pd.Series:
    """
    Session-anchored VWAP (resets at start of day/session).
    Using simple 'day' anchor for now (UTC day change).
    """
    typical_price = (high + low + close) / 3
    pv = typical_price * volume
    
    # Group by date
    df = pd.DataFrame({'pv': pv, 'vol': volume, 'date': times.dt.date})
    
    grouped = df.groupby('date')
    cum_pv = grouped['pv'].cumsum()
    cum_vol = grouped['vol'].cumsum()
    
    return cum_pv / cum_vol

def pivot_points(series: pd.Series, left: int = 3, right: int = 3) -> Tuple[pd.Series, pd.Series]:
    """
    Returns boolean series for pivot highs and lows.
    """
    # Shift approach
    # A point is a pivot high if it's max in [t-left, t+right]
    # We can use rolling max centered.
    
    window = left + right + 1
    
    # For future lookahead (right > 0), we can't do this in strict real-time 
    # unless we delay the signal by 'right' bars.
    # In 'closed bar' processing for signals, if we need right=3, we simply can't know it at current bar t.
    # We check if bar t-right was a pivot.
    
    # Logic: At time T, we can determine if T-right was a pivot.
    # We will return the series aligned to T (so the pivot boolean is True at T for the pivot occurring at T-right? 
    # OR we return aligned to the pivot bar itself, but values are only valid 'right' bars later?)
    
    # Standard approach: Return True at the index of the pivot. 
    # BUT caution: checking is_pivot_high[t] implies analyzing future data [t+1...t+right].
    # So if you use this, you must only access is_pivot_high[t-right] at time t.
    
    rolled_max = series.rolling(window=window, center=True).max()
    rolled_min = series.rolling(window=window, center=True).min()
    
    # Pyt pandas rolling with center=True shifts things.
    # We will implement manually or carefully.
    
    # Let's say we want to know if index `i` is a pivot.
    # It must be > all in [i-left, i-1] AND > all in [i+1, i+right].
    
    # We'll just use a clearer method for pivot *detection* looking back.
    # detect_pivots will return pivots found up to index T (so pivots are effectively 'right' bars ago).
    pass 

def find_divergence(price: pd.Series, osc: pd.Series, lookback: int = 50, left: int = 3, right: int = 3) -> pd.Series:
    """
    Returns 1 for Bullish Div (Price LL, Osc HL), -1 for Bearish Div (Price HH, Osc LH), 0 otherwise.
    Detected at 'right' bars after the pivot.
    """
    # ... Simplified for now
    # We will implement this inside the specific strategy logic to handle state properly.
    return pd.Series(0, index=price.index)
