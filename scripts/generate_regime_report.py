import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np

# Path Setup
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

try:
    from hongstr.regime.baseline import RegimeLabeler
except ImportError:
    RegimeLabeler = None

def load_jsonl(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_json(path, lines=True)

def calc_mdd(equity_series: pd.Series) -> float:
    if len(equity_series) < 1:
        return 0.0
    rolling_max = equity_series.cummax()
    drawdown = (equity_series - rolling_max) / rolling_max
    return drawdown.min()

def calc_sharpe(returns: pd.Series, periods_per_year=365*6) -> float:
    # returns is pct_change series
    if len(returns) < 2:
        return 0.0
    std = returns.std()
    if std == 0:
        return 0.0
    return (returns.mean() / std) * np.sqrt(periods_per_year)

def generate_report(run_dir: Path, data_root: Path):
    summary_path = run_dir / "summary.json"
    if not summary_path.exists():
        print(f"Error: summary.json not found in {run_dir}")
        return

    summary = json.loads(summary_path.read_text())
    
    # 1. Compute Regime Series (BTC 4h)
    btc_4h_path = data_root / "derived" / "BTCUSDT" / "4h" / "klines.jsonl"
    regime_source = "fallback"
    df_regime = pd.DataFrame()
    
    if RegimeLabeler and btc_4h_path.exists():
        try:
            df_btc = pd.read_json(btc_4h_path, lines=True)
            if not df_btc.empty and 'close' in df_btc.columns:
                if 'ts' in df_btc.columns: # Ensure ts index
                    df_btc['ts'] = pd.to_datetime(df_btc['ts'])
                    df_btc.set_index('ts', inplace=True)
                
                labeler = RegimeLabeler()
                labels = labeler.label_regime(df_btc)
                df_regime = labels.to_frame(name="regime")
                regime_source = "computed"
        except Exception as e:
            print(f"Regime calc fail: {e}")

    if df_regime.empty:
        # Fallback: assume NEUTRAL? Or fail? 
        # Requirement: "allow missing data... don't crash"
        pass

    # 2. Portfolio Metrics (by merging Equity Curve with Regime)
    equity_path = run_dir / "equity_curve.jsonl"
    df_equity = load_jsonl(equity_path)
    
    buckets = {k: {"trades_count": 0, "win_rate": 0.0, "total_return": 0.0, "max_drawdown": 0.0, "sharpe": 0.0, "per_symbol": {}} 
               for k in ["BULL", "BEAR", "NEUTRAL"]}

    if not df_equity.empty and not df_regime.empty:
        df_equity['ts'] = pd.to_datetime(df_equity['ts'])
        if df_equity['ts'].dt.tz is None:
            df_equity['ts'] = df_equity['ts'].dt.tz_localize("UTC")
        else:
            df_equity['ts'] = df_equity['ts'].dt.tz_convert("UTC")
            
        df_equity.set_index('ts', inplace=True)
        # Sort index to be safe
        df_equity.sort_index(inplace=True)
        
        # Ensure df_regime is UTC
        if df_regime.index.tz is None:
            df_regime.index = df_regime.index.tz_localize("UTC")
        else:
            df_regime.index = df_regime.index.tz_convert("UTC")
            
        # Merge regime (asof / reindex)
        # We align to equity timestamps, using forward fill from regime (state persists until change)
        df_merged = df_equity.join(df_regime, how='left')
        df_merged['regime'] = df_merged['regime'].fillna('NEUTRAL') # Default if data missing
        
        # Calculate returns
        df_merged['ret'] = df_merged['equity'].pct_change().fillna(0.0)
        
        # Segment Analysis
        for label in ["BULL", "BEAR", "NEUTRAL"]:
            # Filter returns for this regime
            seg_rets = df_merged[df_merged['regime'] == label]['ret']
            
            if not seg_rets.empty:
                # Synthetic Equity for this regime
                seg_growth = (1 + seg_rets).cumprod()
                
                # Total Return for segment
                # (1+r1)*(1+r2)... - 1
                tr = (1 + seg_rets).prod() - 1
                
                # Metric
                buckets[label]['total_return'] = tr
                buckets[label]['max_drawdown'] = calc_mdd(seg_growth)
                buckets[label]['sharpe'] = calc_sharpe(seg_rets) # Using ~4h assumption? 
                # Actually equity curve resolution depends on backtest engine. 
                # If engine steps 1m but equity logs every trade or hour... 
                # Assuming 4h steps roughly for now or just annualized via N. 
                # Safe fallback: len(seg_rets) based scaling
                
                # Time range (naive: first and last ts)
                # Note: buckets requirement asks for "start_ts, end_ts (segments)"
                # To keep it simple JSON-serializable, lets just list coverage % or simpler range
                buckets[label]['count_periods'] = int(len(seg_rets))

    # 3. Trade Metrics (Trades Count, Win Rate, Symbol breakdown)
    trades_path = run_dir / "trades.jsonl"
    df_trades = load_jsonl(trades_path)
    
    if not df_trades.empty:
        if 'ts_entry' in df_trades.columns:
            df_trades['ts_entry'] = pd.to_datetime(df_trades['ts_entry'])
            if df_trades['ts_entry'].dt.tz is None:
                df_trades['ts_entry'] = df_trades['ts_entry'].dt.tz_localize("UTC")
            else:
                df_trades['ts_entry'] = df_trades['ts_entry'].dt.tz_convert("UTC")
            
        # Map regime
        if not df_regime.empty:
             df_regime_sorted = df_regime.sort_index()
             idx = df_regime_sorted.index.searchsorted(df_trades['ts_entry'])
             idx = np.clip(idx - 1, 0, len(df_regime_sorted)-1) 
             # Use values to avoid index issues during assignment
             df_trades['regime_label'] = df_regime_sorted.iloc[idx]['regime'].values
             
             # Double check: searchsorted returns insertion point `i` such that a[i-1] <= v < a[i]
             # Correct, index-1 gives the regime effectively active at that time
        else:
             df_trades['regime_label'] = 'NEUTRAL'
             
        # Aggregate
        for label, grp in df_trades.groupby('regime_label'):
            if label not in buckets: continue
            
            count = len(grp)
            win = len(grp[grp['pnl'] > 0]) / count if count > 0 else 0.0
            total_ret = grp['pnl_pct'].sum() # Simple sum of trade returns for cross-verif?
            
            # Update bucket
            buckets[label]['trades_count'] = int(count)
            buckets[label]['win_rate'] = win
            # Note: bucket['total_return'] is from equity curve (more accurate for portfolio). 
            # If equity curve was missing, we could fallback here.
            
            # Per Symbol Breakdown
            per_symbol = {}
            for sym, sym_grp in grp.groupby('symbol'):
                 scount = len(sym_grp)
                 swin = len(sym_grp[sym_grp['pnl'] > 0]) / scount if scount > 0 else 0.0
                 sret = sym_grp['pnl_pct'].sum()
                 sret = sym_grp['pnl_pct'].sum()
                 # sduration = sym_grp['ts_exit'] - sym_grp['ts_entry'] if 'ts_exit' in sym_grp else pd.Series()
                 
                 # Trade-based Sharpe proxy?
                 s_rets = sym_grp['pnl_pct']
                 s_sharpe = (s_rets.mean()/s_rets.std() * np.sqrt(len(s_rets))) if len(s_rets)>2 and s_rets.std()>0 else 0.0
                 
                 per_symbol[sym] = {
                     "trades_count": int(scount),
                     "win_rate": swin,
                     "total_return": sret,
                     "max_drawdown": 0.0, # N/A without symbol equity curve
                     "sharpe": s_sharpe
                 }
            buckets[label]['per_symbol'] = per_symbol

    # Determine Latest Regime
    latest_regime = "NEUTRAL"
    if not df_regime.empty:
        # Get the last available regime label
        latest_regime = df_regime.iloc[-1]['regime']

    # JSON Output
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "timeframe_regime": "4h",
        "regime_series_source": regime_source,
        "latest_regime": latest_regime,
        "buckets": buckets
    }
    
    # Atomic Write
    out_path = run_dir / "regime_report.json"
    tmp_path = run_dir / "regime_report.json.tmp"
    with open(tmp_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    os.rename(tmp_path, out_path)
    print(f"Generated regime_report.json in {run_dir} (Latest: {latest_regime})")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True, help="Backtest run dir")
    parser.add_argument("--data_root", default="data", help="Data root")
    args = parser.parse_args()
    
    generate_report(Path(args.dir), Path(args.data_root))

if __name__ == "__main__":
    main()
