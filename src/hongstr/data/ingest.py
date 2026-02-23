import requests
import pandas as pd
import time
from datetime import datetime
from hongstr.config import BINANCE_API_KEY, DATA_DIR

BASE_URL = "https://fapi.binance.com"
LIMIT = 1500  # Max candles per request

def fetch_klines(symbol: str, start_ts: int, end_ts: int) -> pd.DataFrame:
    """
    Fetch 1m klines from Binance Futures.
    start_ts, end_ts: milliseconds
    """
    klines = []
    current_start = start_ts
    
    while current_start < end_ts:
        url = f"{BASE_URL}/fapi/v1/klines"
        params = {
            "symbol": symbol,
            "interval": "1m",
            "startTime": current_start,
            "endTime": end_ts,
            "limit": LIMIT
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Error fetching {symbol} at {current_start}: {e}")
            time.sleep(5)
            continue
            
        if not data:
            break
            
        klines.extend(data)
        last_close_time = data[-1][6]
        current_start = last_close_time + 1
        
        # Rate limit
        time.sleep(0.1)
        
    if not klines:
        return pd.DataFrame()
        
    # Columns based on Binance API
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "number_of_trades",
        "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
    ]
    
    df = pd.DataFrame(klines, columns=cols)
    
    # Type conversion
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for c in numeric_cols:
        df[c] = df[c].astype(float)
        
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("open_time")
    
    # Keep only essential columns + Ensure sorted
    df = df[numeric_cols].sort_index()
    return df

def save_klines(df: pd.DataFrame, symbol: str):
    """
    Save to Parquet, partitioned by symbol/date (conceptually).
    Phase 0: Simple append/overwrite per symbol file for simplicity or one big file?
    Implementation: one parquet file per symbol for 1m data is robust enough for 2020-now (approx 2M rows).
    """
    path = DATA_DIR / f"{symbol}_1m.parquet"
    if path.exists():
        existing = pd.read_parquet(path)
        # Combine and deduplicate
        combined = pd.concat([existing, df])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        combined.to_parquet(path)
    else:
        df.to_parquet(path)
    print(f"Saved {len(df)} rows for {symbol} to {path}")
