import sys
from pathlib import Path
# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
from datetime import datetime
import pytz
from hongstr.config import DATA_DIR, TIMEZONE

def inspect_timestamps(symbol: str = "BTCUSDT"):
    path = DATA_DIR / f"{symbol}_1m.parquet"
    if not path.exists():
        print(f"File not found: {path}")
        return

    df = pd.read_parquet(path)
    if df.empty:
        print("Dataframe is empty.")
        return

    tz = pytz.timezone(TIMEZONE)
    
    print(f"--- Inspecting {symbol} ---")
    print(f"Total rows: {len(df)}")
    
    # Check start/end
    start_ts_utc = df.index[0]
    end_ts_utc = df.index[-1]
    
    start_ts_local = start_ts_utc.tz_localize('UTC').tz_convert(tz)
    end_ts_local = end_ts_utc.tz_localize('UTC').tz_convert(tz)
    
    print(f"Start (UTC):   {start_ts_utc}")
    print(f"Start (Local): {start_ts_local}")
    print(f"End (UTC):     {end_ts_utc}")
    print(f"End (Local):   {end_ts_local}")
    
    # Check alignment
    # Verify minutes are aligned (seconds=0, microseconds=0)
    aligned_start = start_ts_local.second == 0 and start_ts_local.microsecond == 0
    aligned_end = end_ts_local.second == 0 and end_ts_local.microsecond == 0
    
    print(f"Start Aligned? {aligned_start}")
    print(f"End Aligned?   {aligned_end}")
    
    # Check sample rows alignment
    sample = df.sample(min(10, len(df)))
    unaligned_count = 0
    for ts in sample.index:
        ts_local = ts.tz_localize('UTC').tz_convert(tz)
        if ts_local.second != 0 or ts_local.microsecond != 0:
            unaligned_count += 1
            print(f"Unaligned: {ts} -> {ts_local}")
            
    if unaligned_count == 0:
        print("Sampled rows are all minute-aligned.")
    else:
        print(f"WARNING: Found {unaligned_count} unaligned rows in sample.")

if __name__ == "__main__":
    inspect_timestamps()
