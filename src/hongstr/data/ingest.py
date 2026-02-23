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
    BASE_URLS = [
        "https://fapi.binance.com",
        "https://data-api.binance.vision",
        "https://api.binance.com"
    ]
    
    klines = []
    current_start = start_ts
    
    # Watchdog and Backoff tracking
    last_progress_time = time.time()
    MAX_STALL_S = 900  # 15 minutes max without progress
    backoff_s = 5
    MAX_BACKOFF_S = 60
    endpoint_idx = 0
    
    while current_start < end_ts:
        # Check watchdog timeout
        if time.time() - last_progress_time > MAX_STALL_S:
            print(f"WARN: [WATCHDOG] Ingest stalled for > 15m on {symbol}. Aborting fetch.")
            break
            
        base_url = BASE_URLS[endpoint_idx % len(BASE_URLS)]
        # For data-api.binance.vision and api.binance.com, the path might be /api/v3/klines if fapi fails,
        # but the user requested minimal changes. We will try /fapi/v1/klines on the fallback.
        url = f"{base_url}/fapi/v1/klines"
        
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
            
            # Reset backoff and watchdog on success
            backoff_s = 5
            last_progress_time = time.time()
            endpoint_idx = 0  # Revert to primary on success
            
        except Exception as e:
            print(f"Error fetching {symbol} at {current_start} via {base_url}: {e}")
            endpoint_idx += 1  # Fallback to next endpoint
            
            print(f"Retrying in {backoff_s}s... (endpoint_idx={endpoint_idx % len(BASE_URLS)})")
            time.sleep(backoff_s)
            backoff_s = min(backoff_s * 2, MAX_BACKOFF_S)  # Exponential backoff
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
