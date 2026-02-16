import pandas as pd
from typing import List, Optional
from .types import Bar

def floor_ts_to_tf(ts: pd.Timestamp, tf: str) -> pd.Timestamp:
    """Floor timestamp to timeframe start."""
    # Simple pandas floor
    # 1m, 5m, 15m, 1h, 4h
    if tf == "1m":
        return ts.floor("1min")
    elif tf == "5m":
        return ts.floor("5min")
    elif tf == "15m":
        return ts.floor("15min")
    elif tf == "1h":
        return ts.floor("1h")
    elif tf == "4h":
        # 4h alignment can be tricky depending on start of day. 
        # Assuming standard UTC 00:00 alignment for now.
        return ts.floor("4h")
    else:
        raise ValueError(f"Unsupported timeframe: {tf}")

def resample_bars(bars_1m: List[Bar], tf: str) -> List[Bar]:
    """
    Resample a list of 1m bars to target timeframe.
    Only returns CLOSED bars for the target timeframe.
    Assumes incoming bars are sorted by time.
    """
    if not bars_1m:
        return []
    
    if tf == "1m":
        # Just return closed 1m bars
        return [b for b in bars_1m if b.closed]

    # Convert to DataFrame for easier resampling
    data = []
    for b in bars_1m:
        data.append({
            "ts": b.ts,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        })
    
    df = pd.DataFrame(data)
    df.set_index("ts", inplace=True)
    
    # Map tf string to pandas offset alias
    offset_map = {
        "5m": "5min",
        "15m": "15min",
        "1h": "1h",
        "4h": "4h"
    }
    
    if tf not in offset_map:
         raise ValueError(f"Unsupported timeframe: {tf}")
         
    rule = offset_map[tf]
    
    resampled = df.resample(rule, closed='left', label='left').agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    })
    
    # Filter out incomplete bars?
    # We only want to emit a bar when it is "closed".
    # A bar at T is closed when we have seen data >= T + tf.
    # OR if we trust the input stream is continuous and we just finished the window.
    # But resample() will create a row for the bucket as long as there is data.
    
    # We need to know which of these resampled bars are actually "complete".
    # Simple heuristic: If the last 1m bar timestamp >= resampled_bar_end_time, then the resampled bar is closed.
    
    last_1m_ts = bars_1m[-1].ts
    
    result_bars = []
    
    for ts, row in resampled.iterrows():
        # Calculate end time of this bar
        bar_start = pd.Timestamp(ts)
        bar_end = bar_start + pd.Timedelta(rule)
        
        # If we have data past or exactly at the end boundary logic...
        # Actually standard definition: a 1h bar [10:00, 11:00) is closed when we see 11:00 data (or later).
        # We are processing 1m bars. 
        # If last_1m_ts is 11:00, then the 10:00-11:00 bar is closed.
        
        is_closed = last_1m_ts >= bar_end
        
        if is_closed and not row.isna().any():
            result_bars.append(Bar(
                ts=bar_start,
                symbol=bars_1m[0].symbol, # Assume same symbol
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                closed=True
            ))
            
    return result_bars
