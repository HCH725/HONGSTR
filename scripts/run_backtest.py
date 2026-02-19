import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.backtest.engine import BacktestEngine
from hongstr.backtest.metrics import calc_metrics
from hongstr.semantics.core import SemanticsV1
from hongstr.signal.resample import resample_bars
from hongstr.signal.strategies.vwap_supertrend import VWAPSupertrendStrategy
from hongstr.signal.types import Bar


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
    parser.add_argument("--out_dir", type=str, help="Explicit output directory")
    parser.add_argument("--run_id", type=str, help="Explicit Run ID (default: timestamp)")
    args = parser.parse_args()

    # 1. Prepare Environment
    symbols = [s.strip() for s in args.symbols.split(",")]
    timeframes = [tf.strip() for tf in args.timeframes.split(",")]

    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    if args.out_dir:
        out_dir = Path(args.out_dir)
        run_id = args.run_id if args.run_id else "custom"
        # If run_id provided with out_dir, we just use out_dir as is, run_id is for metadata.
    else:
        run_id = args.run_id if args.run_id else datetime.utcnow().strftime("%H%M%S")
        out_dir = Path(args.out_root) / date_str / run_id

    out_dir.mkdir(parents=True, exist_ok=True)

    semantics = SemanticsV1(
        taker_fee_rate=args.fee_bps / 10000.0,
        slippage_bps=args.slippage_bps
    )

    # Strategy Init
    # We will Init strategy inside the loop to allow per-TF config

    all_results = {}

    print(f"--- Starting Backtest Run: {run_id} ---")

    for symbol in symbols:
        print(f"Processing {symbol}...")
        df_1m = load_1m_data(args.data_root, symbol)

        if df_1m.empty:
            py_exe = sys.executable
            print(f"Data missing for {symbol}. Expected in {args.data_root}/{symbol}/1m/")
            print(f"Please run: {py_exe} scripts/ingest_historical.py --symbol {symbol}")
            print(f"Then: {py_exe} scripts/aggregate_data.py --symbol {symbol}")
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
            # Optimization: Use itertuples for much faster iteration than iterrows
            bars_1m = [
                Bar(ts=row.Index, symbol=symbol, open=row.open, high=row.high, low=row.low, close=row.close, volume=row.volume, closed=True)
                for row in df_1m.itertuples()
            ]
            resampled_bars = resample_bars(bars_1m, tf)

            if not resampled_bars:
                print(f"    Insufficient data for resampling to {tf}")
                continue

            # Strategy Configuration per Timeframe
            # Defaults
            atr_period = 10
            atr_mult = 3.0

            if tf == "4h":
                # Looser for 4h to generate more signals?
                # Or just standard params might be too tight or too lagging.
                # Let's try to make it more sensitive for 4h:
                # smaller period or smaller mult?
                # Actually default config ST_ATR_PERIOD=10, MULT=3.
                # Maybe 4h needs shorter period to react faster? e.g. 7, 2.0?
                atr_period = 10
                atr_mult = 2.0 # Detect trend changes earlier

            # Init Strategy for this run
            # Important: The strategy class checks env var STRATEGY_TIMEFRAME_SIGNAL.
            # We must force it to accept current TF.
            os.environ["STRATEGY_TIMEFRAME_SIGNAL"] = tf

            if args.strategy == "vwap_supertrend":
                strategy = VWAPSupertrendStrategy(atr_period=atr_period, atr_mult=atr_mult)
            else:
                 sys.exit(1)

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
                # Optimization: Strategy only needs last N+5 bars
                lookback = atr_period + 20
                start_idx = max(0, idx - lookback + 1)
                current_bars = resampled_bars[start_idx:idx+1]

                # vwap_supertrend.on_bars wants (symbol, tf, bars)
                signal_event = strategy.on_bars(symbol, tf, current_bars)
                if signal_event:
                    return signal_event.direction
                return None

            result = engine.run(symbol, strategy_stub=strategy_wrapper)

            # Capture Debug Counts
            result['debug_counts'] = strategy.debug_counts

            res_key = f"{symbol}_{tf}"
            all_results[res_key] = result

            # Save per-run trades and equity if needed, but we'll aggregate

    # 3. Aggregation & Export
    if not all_results:
        print("No backtest results produced.")
        sys.exit(1)

    # Combine trades from all symbols/TFs
    all_trades = []
    equity_dfs = []

    for k, res in all_results.items():
        all_trades.extend(res['trades'])

        # Log Counts
        counts = res.get('counts', {})
        bars_n = counts.get('bars', 0)
        sigs_n = counts.get('signals', 0)
        trds_n = counts.get('trades', 0)
        reason = res.get('no_trades_reason', '')
        print(f"  {k}: Bars={bars_n}, Signals={sigs_n}, Trades={trds_n} {f'({reason})' if reason else ''}")

        # Prepare for aggregation
        eq_curve = res.get('equity_curve', [])
        if eq_curve:
            df_eq = pd.DataFrame(eq_curve)
            df_eq['ts'] = pd.to_datetime(df_eq['ts'])
            df_eq.set_index('ts', inplace=True)
            # Use just the equity column, rename to key to distinguish
            equity_dfs.append(df_eq['equity'].rename(k))

    # Global Summary
    if not equity_dfs:
        print("No equity curves generated.")
        # Fallback empty metrics
        global_metrics = calc_metrics(pd.DataFrame(), [])
    else:
        # Align all curves
        # Use outer join to cover full range.
        # Missing values (e.g. before start or after end) should be filled.
        # Before start: initial_capital. After end: last equity.
        agg_df = pd.concat(equity_dfs, axis=1)

        # ffill/bfill defaults.
        # If a backtest hasn't started yet for a symbol, its equity is effectively initial_capital.
        agg_df.fillna(args.initial_capital, inplace=True)

        # Sum equities?
        # If we run 3 symbols, we have 3 independent accounts of 10k each.
        # Total Portfolio Value = Sum(Equity_i).
        agg_equity = agg_df.sum(axis=1)

        # Re-calc metrics on aggregated curve
        # calc_metrics expects a DataFrame with 'equity' column
        metrics_input_df = pd.DataFrame(agg_equity, columns=['equity'])
        # Also need cash/pos for perfect metrics? calc_metrics mainly uses equity for Sharpe/DD.
        # It calculates returns from equity diffs.

        try:
            global_metrics = calc_metrics(metrics_input_df, all_trades)
        except Exception as e:
            print(f"Error calculating global metrics: {e}")
            global_metrics = {}

    summary = {
        "run_id": run_id,
        "timestamp": datetime.utcnow().isoformat(),
        **global_metrics, # total_return, sharpe, max_dd, etc.
        "per_symbol": {
            k: {**res['metrics'], "debug": res.get('debug_counts', {})}
            for k, res in all_results.items()
        },
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

    # Check if GLOBAL filtering happened
    if len(all_trades) == 0:
        summary["no_trades_reason"] = "No trades in any symbol/timeframe."

    # Save Files
    # Atomic write for summary.json to avoid partial reads by verify scripts
    temp_summary = out_dir / "summary.json.tmp"
    with open(temp_summary, 'w') as f:
        json.dump(summary, f, indent=2)
    temp_summary.rename(out_dir / "summary.json")

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

    print("--- Backtest Finished ---")
    print(f"Results saved to: {out_dir}")
    print(f"COMPLETED_DIR={out_dir}")

if __name__ == "__main__":
    main()
