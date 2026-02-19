import pandas as pd

def check_continuity(df: pd.DataFrame, timeframe: str = '1m') -> pd.DataFrame:
    """
    Check for missing timestamps in the DataFrame index.
    Returns a DataFrame of gaps (start, end, duration).
    """
    if df.empty:
        return pd.DataFrame()
        
    # Expected freq
    freq_map = {'1m': '1T', '5m': '5T', '15m': '15T', '1h': '1H', '4h': '4H'}
    freq = freq_map.get(timeframe, '1T')
    
    full_idx = pd.date_range(start=df.index[0], end=df.index[-1], freq=freq)
    missing = full_idx.difference(df.index)
    
    if len(missing) == 0:
        return pd.DataFrame()
        
    # Group missing timestamps into contiguous ranges
    gaps = []
    if len(missing) > 0:
        # Detect consecutive groups
        series = pd.Series(missing)
        diffs = series.diff()
        # Non-consecutive jumps imply new group (diff > freq)
        # Simple approach: iterate
        pass # Too slow for large sets?
        
        # Faster approach:
        # Create a boolean series aligned to full index
        # True = missing
        # Find runs of True
        pass

    # Simplified list for reporting for now
    return pd.DataFrame({'missing_timestamp': missing})

def report_metrics(df: pd.DataFrame, timeframe: str = '1m') -> dict:
    if df.empty:
        return {"result": "empty"}
        
    freq_map = {'1m': '1min', '5m': '5min', '15m': '15min', '1h': '1h', '4h': '4h'}
    freq = freq_map.get(timeframe, '1min')
    
    full_idx = pd.date_range(start=df.index[0], end=df.index[-1], freq=freq)
    total_expected = len(full_idx)
    actual = len(df)
    missing_count = total_expected - actual
    missing_ratio = missing_count / total_expected if total_expected > 0 else 0
    
    return {
        "start": df.index[0],
        "end": df.index[-1],
        "total_expected": total_expected,
        "actual": actual,
        "missing_count": missing_count,
        "missing_ratio": missing_ratio
    }
