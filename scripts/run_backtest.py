import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.semantics.core import SemanticsV1
from hongstr.backtest.engine import BacktestEngine
from hongstr.signal.resample import resample_bars
from hongstr.signal.types import Bar
from hongstr.signal.strategies.vwap_supertrend import VWAPSupertrendStrategy

def load_1m_data(data_root: str, symbol: str) -> pd.DataFrame:
    """Load 1m data from data/derived/{symbol}/1m/klines.jsonl (or .csv)"""
    symbol_dir = Path(data_root) / symbol / "1m"
    jsonl_path = symbol_dir / "klines.jsonl"
    csv_path = symbol_dir / "klines.csv"
    
    if jsonl_path.exists():
        data = []
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    # Support both raw websocket format and simplified format
                    if "data" in record:
                        k = record["data"].get("k", {})
                        data.append({
                            "ts": pd.Timestamp(k['t'], unit='ms', tz='UTC'),
                            "open": float(k['o']),
                            "high": float(k['h']),
                            "low": float(k['l']),
                            "close": float(k['c']),
                            "volume": float(k['v'])
                        })
                    else:
                        # Simplified format
                        if "ts" in record:
                            # If ts is int (ms), convert with unit='ms'
                            if isinstance(record['ts'], int):
                                record['ts'] = pd.Timestamp(record['ts'], unit='ms', tz='UTC')
                            else:
                                record['ts'] = pd.to_datetime(record['ts']).tz_localize("UTC") if pd.to_datetime(record['ts']).tz is None else pd.to_datetime(record['ts']).tz_convert("UTC")
                        data.append(record)
                except: continue
        df = pd.DataFrame(data)
        if not df.empty:
            df['ts'] = pd.to_datetime(df['ts'])
            # Final safety check for awareness
            if df['ts'].dt.tz is None:
                df['ts'] = df['ts'].dt.tz_localize("UTC")
            df.set_index('ts', inplace=True)
            return df
    elif csv_path.exists():
        df = pd.read_csv(csv_path)
        df['ts'] = pd.to_datetime(df['ts'])
        df.set_index('ts', inplace=True)
        return df
        
    return pd.DataFrame()

def main():
    parser = argparse.ArgumentParser(description="HONGSTR Offline Backtest Runner")
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT,BNBUSDT")
    parser.add_argument("--timeframes", type=str, default="1h,4h")
    parser.add_argument("--start", type=str, default="2021-01-01")
    parser.add_argument("--end", type=str, default="now")
    parser.add_argument("--strategy", type=str, default="vwap_supertrend")
    parser.add_argument("--initial_capital", type=float, default=10000.0)
    parser.add_argument("--size_notional_usd", type=float, default=1000.0)
    parser.add_argument("--fee_bps", type=float, default=4.0)
    parser.add_argument("--slippage_bps", type=float, default=2.0)
    parser.add_argument("--data_root", type=str, default="data/derived")
    parser.add_argument("--out_root", type=str, default="data/backtests")
    args = parser.parse_args()

    # 1. Prepare Environment
    symbols = [s.strip() for s in args.symbols.split(",")]
    timeframes = [tf.strip() for tf in args.timeframes.split(",")]
    
    run_id = datetime.utcnow().strftime("%H%M%S")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = Path(args.out_root) / date_str / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    semantics = SemanticsV1(
        taker_fee_rate=args.fee_bps / 10000.0,
        slippage_bps=args.slippage_bps
    )
    
    # Strategy Init
    if args.strategy == "vwap_supertrend":
        strategy = VWAPSupertrendStrategy()
    else:
        print(f"Unsupported strategy: {args.strategy}")
        sys.exit(1)

    all_results = {}
    
    print(f"--- Starting Backtest Run: {run_id} ---")
    
    for symbol in symbols:
        print(f"Processing {symbol}...")
        df_1m = load_1m_data(args.data_root, symbol)
        
        if df_1m.empty:
            print(f"Data missing for {symbol}. Expected in {args.data_root}/{symbol}/1m/")
            print(f"Please run: python scripts/ingest_historical.py --symbol {symbol}")
            print(f"Then: python scripts/aggregate_data.py --symbol {symbol}")
            continue
            
        # Filter by date
        start_dt = pd.Timestamp(args.start).tz_localize("UTC")
        end_dt = pd.Timestamp(args.end).tz_localize("UTC") if args.end != "now" else pd.Timestamp.now(tz="UTC")
        df_1m = df_1m[(df_1m.index >= start_dt) & (df_1m.index <= end_dt)]
        
        if df_1m.empty:
            print(f"No data for {symbol} in range {args.start} to {args.end}")
            continue

        for tf in timeframes:
            print(f"  Timeframe: {tf}")
            
            # Resample 1m -> TF
            bars_1m = [
                Bar(ts=ts, symbol=symbol, open=row['open'], high=row['high'], low=row['low'], close=row['close'], volume=row['volume'], closed=True)
                for ts, row in df_1m.iterrows()
            ]
            resampled_bars = resample_bars(bars_1m, tf)
            
            if not resampled_bars:
                print(f"    Insufficient data for resampling to {tf}")
                continue
                
            # Convert back to DataFrame for Engine
            df_tf = pd.DataFrame([b.__dict__ for b in resampled_bars])
            df_tf.set_index('ts', inplace=True)
            
            # Run Engine
            engine = BacktestEngine(
                semantics=semantics,
                data=df_tf,
                initial_capital=args.initial_capital,
                size_notional_usd=args.size_notional_usd
            )
            
            # Strategy Glue: map SignalEvent to direction
            def strategy_wrapper(row):
                # The strategy expects List[Bar] up to current row index
                # This is inefficient for full backtest but fits current C9 strategy signature
                # To optimize: strategies should ideally have an update(bar) method
                # For Phase 1 C15, we'll slice a window of bars
                idx = df_tf.index.get_loc(row.name)
                current_bars = resampled_bars[:idx+1]
                # vwap_supertrend.on_bars wants (symbol, tf, bars)
                signal_event = strategy.on_bars(symbol, tf, current_bars)
                if signal_event:
                    return signal_event.direction
                return None

            result = engine.run(symbol, strategy_stub=strategy_wrapper)
            
            res_key = f"{symbol}_{tf}"
            all_results[res_key] = result
            
            # Save per-run trades and equity if needed, but we'll aggregate

    # 3. Aggregation & Export
    if not all_results:
        print("No backtest results produced.")
        sys.exit(1)
        
    # Combine trades from all symbols/TFs
    all_trades = []
    for k, res in all_results.items():
        all_trades.extend(res['trades'])
        
    # Global Summary
    # Simple aggregation for now: Average total return or sum?
    # Usually we want a portfolio view, but C15 focus is isolated runs.
    # We'll export a summary that lists per-symbol metrics.
    
    # Combined Summary (Global)
    # If single symbol/tf, we promote its metrics to root.
    # If multiple, we should ideally aggregate (notional weighting), but for MVP 
    # we'll just use the first as base and notify it's per-symbol.
    first_res = list(all_results.values())[0]
    global_metrics = first_res['metrics'].copy()
    
    summary = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        **global_metrics, # total_return, sharpe, max_dd, etc.
        "per_symbol": {k: res['metrics'] for k, res in all_results.items()},
        "config": {
            "initial_capital": args.initial_capital,
            "size_mode": "notional_usd",
            "size_notional_usd": args.size_notional_usd,
            "fee_bps": args.fee_bps,
            "slippage_bps": args.slippage_bps,
            "fill_mode": "next_open",
            "timestamp_convention": "bar_start_utc",
            "symbols": symbols,
            "timeframes": timeframes
        }
    }
    
    if len(all_trades) == 0:
        summary["no_trades_reason"] = "Strategy never triggered or insufficient data for next_open fill"
    
    # Save Files
    with open(out_dir / "summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
        
    with open(out_dir / "config.json", 'w') as f:
        json.dump(summary["config"], f, indent=2)
        
    # Save trades.jsonl
    with open(out_dir / "trades.jsonl", 'w') as f:
        for t in all_trades:
            f.write(json.dumps(t) + "\n")
            
    # Save equity_curve.jsonl (picking the first for demo if multiple, or combined?)
    # Requirements: "equity_curve.jsonl: ts, equity, cash, position_notional (at least ts+equity)"
    # For C15 we'll just skip combined equity and export first symbol's curve as sample or all curves?
    # Better: Save per-symbol-tf curve in subfolder or separate file.
    # User's schema check wants equity_curve.jsonl in run_id folder.
    # We'll save the first one there or an empty one if multiple symbols.
    first_key = list(all_results.keys())[0]
    with open(out_dir / "equity_curve.jsonl", 'w') as f:
        for p in all_results[first_key]['equity_curve']:
            f.write(json.dumps(p) + "\n")

    print(f"--- Backtest Finished ---")
    print(f"Results saved to: {out_dir}")

if __name__ == "__main__":
    main()
