import sys
from pathlib import Path
# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
import time
from datetime import datetime, timedelta
from hongstr.data.ingest import fetch_klines, save_klines
from hongstr.data.quality import report_metrics
from hongstr.config import SYMBOLS, INTERVALS, DATA_DIR

def run_dry_run():
    print("Starting Dry Run...")
    
    # Fetch last 1 hour
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(hours=1)
    
    start_ts = int(start_dt.timestamp() * 1000)
    end_ts = int(end_dt.timestamp() * 1000)
    
    symbol = "BTCUSDT" # Test with one symbol
    print(f"Fetching {symbol} from {start_dt} to {end_dt}...")
    
    df = fetch_klines(symbol, start_ts, end_ts)
    print(f"Fetched {len(df)} rows.")
    
    if df.empty:
        print("No data fetched!")
        return
        
    # Check Quality
    metrics = report_metrics(df, "1m")
    print("Quality Metrics:", metrics)
    
    # Save
    save_klines(df, symbol)
    
    # Verify file exists
    path = DATA_DIR / f"{symbol}_1m.parquet"
    if path.exists():
        print(f"Verified: {path} exists.")
        saved_df = pd.read_parquet(path)
        print(f"Read back {len(saved_df)} rows from parquet.")
    else:
        print(f"Error: {path} not found.")

if __name__ == "__main__":
    run_dry_run()
