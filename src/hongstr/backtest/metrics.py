import pandas as pd
import numpy as np

def calc_metrics(equity_curve: pd.DataFrame, trades: list) -> dict:
    """
    Calculate CAGR, MaxDD, Sharpe, etc.
    equity_curve: DataFrame with 'equity' column and DatetimeIndex.
    """
    if equity_curve.empty:
        return {}
        
    start_eq = equity_curve['equity'].iloc[0]
    end_eq = equity_curve['equity'].iloc[-1]
    
    # CAGR
    duration_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if duration_days > 0:
        cagr = (end_eq / start_eq) ** (365 / duration_days) - 1
    else:
        cagr = 0.0
        
    # Drawdown
    equity_curve['peak'] = equity_curve['equity'].cummax()
    equity_curve['dd'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
    max_dd = equity_curve['dd'].min()
    
    # Sharpe (daily)
    # Resample to daily returns
    daily = equity_curve['equity'].resample('D').last().dropna()
    returns = daily.pct_change().dropna()
    if len(returns) > 1:
        sharpe = returns.mean() / returns.std() * np.sqrt(365)
    else:
        sharpe = 0.0
        
    return {
        "start_equity": start_eq,
        "end_equity": end_eq,
        "cagr": cagr,
        "max_dd": max_dd,
        "sharpe": sharpe,
        "total_trades": len(trades)
    }

def filter_by_split(equity_curve: pd.DataFrame, trades: list, split: str) -> tuple:
    """
    Filter equity curve and trades by OOS split.
    TRAIN: 2020-01-01 -> 2022-12-31
    VAL:   2023-01-01 -> 2023-12-31
    OOS:   2024-01-01 -> Now
    """
    splits = {
        "TRAIN": ("2020-01-01", "2022-12-31"),
        "VAL":   ("2023-01-01", "2023-12-31"),
        "OOS":   ("2024-01-01", "2099-12-31")
    }
    
    if split not in splits:
        return equity_curve, trades
        
    start_str, end_str = splits[split]
    start_dt = pd.Timestamp(start_str).tz_localize("Asia/Taipei") if equity_curve.index.tz else pd.Timestamp(start_str)
    end_dt = pd.Timestamp(end_str).tz_localize("Asia/Taipei") + pd.Timedelta(hours=23, minutes=59, seconds=59) if equity_curve.index.tz else pd.Timestamp(end_str)
    
    # Handle TZ mismatch if explicit
    # Assuming equity_curve is already TZ-aware (Asia/Taipei)
    
    sub_curve = equity_curve[(equity_curve.index >= start_dt) & (equity_curve.index <= end_dt)]
    
    full_trades_df = pd.DataFrame(trades)
    if not full_trades_df.empty and 'entry_time' in full_trades_df.columns:
         # Filter trades based on entry time
         # Ensure entry_time is comparable
         sub_trades_df = full_trades_df[(full_trades_df['entry_time'] >= start_dt) & (full_trades_df['entry_time'] <= end_dt)]
         sub_trades = sub_trades_df.to_dict('records')
    else:
        sub_trades = []
        
    return sub_curve, sub_trades
