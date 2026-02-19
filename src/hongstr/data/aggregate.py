import pandas as pd

def resample_klines(df_1m: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample 1m klines to target timeframe (5m, 15m, 1h, 4h).
    Aligns to GMT+8 if needed, but since timestamps are UTC (from Binance),
    we handle alignment by offsets if pandas default resample isn't sufficient.
    
    Binance timestamps are UTC.
    GMT+8 alignment:
    - 1h bar at 00:00 GMT+8 is 16:00 UTC (prev day).
    - Standard pandas resample('1H') on UTC index aligns to 00:00 UTC.
    - 00:00 UTC is 08:00 GMT+8. So '1H' on UTC *is* aligned with GMT+8 hours (just shifted).
    - 4h bar: 00:00, 04:00, 08:00 GMT+8.
      00:00 GMT+8 = 16:00 UTC.
      04:00 GMT+8 = 20:00 UTC.
      08:00 GMT+8 = 00:00 UTC.
      So using '4H' on UTC starting at 00:00 UTC covers [00:00, 04:00) UTC which is [08:00, 12:00) GMT+8.
      This aligns perfectly with standard 4h boundaries.
      
    So standard 'resample' works fine on UTC index for 1h/4h alignment.
    """
    if timeframe == '1m':
        return df_1m.copy()
        
    rule_map = {
        '5m': '5min',
        '15m': '15min',
        '1h': '1h',
        '4h': '4h'
    }
    
    rule = rule_map.get(timeframe)
    if not rule:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
        
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }
    
    resampled = df_1m.resample(rule).agg(agg_dict)
    
    # Drop rows that are fully NaN (time gaps) - or keep them to show gaps? 
    # Spec says "detect missing", usually best to drop empty bars and let Quality Gate report gaps.
    resampled = resampled.dropna()
    
    return resampled
