import sys
from pathlib import Path
# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pandas as pd
from hongstr.semantics.core import SemanticsV1
from hongstr.backtest.engine import BacktestEngine
from hongstr.config import DATA_DIR
import hongstr.data.aggregate as agg

def run_smoke_test():
    print("Running Backtest Smoke Test on BTCUSDT...")
    
    # Load 1m data
    parquet_path = DATA_DIR / "BTCUSDT_1m.parquet"
    if not parquet_path.exists():
        print("No data found. Please run C2 ingestion first.")
        return
        
    df_1m = pd.read_parquet(parquet_path)
    if df_1m.empty:
        print("Data is empty.")
        return

    # Aggregate to 1h
    print(f"Aggregating {len(df_1m)} 1m rows to 1h...")
    df_1h = agg.resample_klines(df_1m, "1h")
    print(f"Aggregated to {len(df_1h)} 1h rows.")
    
    if df_1h.empty:
        print("1h Data is empty.")
        return

    # Semantics
    sem = SemanticsV1()
    
    # Engine
    engine = BacktestEngine(sem, df_1h)
    
    # Dummy Strategy: Buy if Close > Open (Green Candle), Sell if Close < Open (Red Candle)
    # Just to generate trades
    def dummy_strategy(row):
        # We need state to not churn every bar
        # Simple: Buy at beginning, Hold?
        # Or: MA crossover stub? Need history.
        # Simplest: Buy if Close > Open and Position == 0. Exit if Close < Open and Position != 0.
        is_green = row['close'] > row['open']
        
        if is_green:
            return 'BUY' # Engine handles "if pos==0" check roughly, but better to be explicit in signal?
                         # Engine _open_position checks if pos!=0 and returns. So safe to spam BUY.
        else:
            return 'EXIT'
            
    results = engine.run(dummy_strategy)
    
    print("\n--- Run Summary ---")
    print(f"Semantics Version: {results['semantics_version']}")
    print(f"Total Trades: {len(results['trades'])}")
    metrics = results['full_metrics']
    print(f"Start Equity: {metrics.get('start_equity')}")
    print(f"End Equity:   {metrics.get('end_equity')}")
    print(f"Sharpe:       {metrics.get('sharpe')}")
    print(f"MaxDD:        {metrics.get('max_dd')}")
    
    print("\n--- OOS Splits ---")
    for split, m in results['splits'].items():
        if m:
            print(f"{split}: Trades={m.get('total_trades')}, Sharpe={m.get('sharpe')}")
        else:
            print(f"{split}: No data")

if __name__ == "__main__":
    run_smoke_test()
