import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

def calc_metrics(equity_curve: pd.DataFrame, trades: list) -> dict:
    """
    Calculate performance metrics.
    equity_curve: DataFrame with 'equity', 'cash', 'position_notional' and DatetimeIndex.
    """
    if equity_curve.empty:
        return {}
        
    start_eq = float(equity_curve['equity'].iloc[0])
    end_eq = float(equity_curve['equity'].iloc[-1])
    total_return = (end_eq / start_eq) - 1 if start_eq > 0 else 0.0
    
    # CAGR
    duration = (equity_curve.index[-1] - equity_curve.index[0])
    duration_days = duration.total_seconds() / 86400
    if duration_days > 0 and start_eq > 0 and end_eq > 0:
        cagr = (end_eq / start_eq) ** (365 / duration_days) - 1
    else:
        cagr = 0.0
        
    # Drawdown
    equity_curve['peak'] = equity_curve['equity'].cummax()
    equity_curve['dd'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
    max_dd = float(equity_curve['dd'].min())
    
    # Sharpe (Daily Sampling)
    # Resample equity to daily (last price of day)
    daily_equity = equity_curve['equity'].resample('D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()
    
    sharpe = None
    if len(daily_returns) > 1:
        std = daily_returns.std()
        if std > 0:
            sharpe = (daily_returns.mean() / std) * np.sqrt(365)
    
    # Exposure Time
    # Fraction of bars where position_notional != 0
    if 'position_notional' in equity_curve.columns:
        exposure_bars = (equity_curve['position_notional'] != 0).sum()
        exposure_time = float(exposure_bars / len(equity_curve))
    else:
        exposure_time = 0.0

    # Trade Metrics
    trades_count = len(trades)
    win_rate = 0.0
    avg_trade_return = 0.0
    
    if trades_count > 0:
        profitable = [t for t in trades if t.get('pnl', 0) > 0]
        win_rate = len(profitable) / trades_count
        
        returns = []
        for t in trades:
            # pnl_pct or manual calc
            pnl = t.get('pnl', 0)
            entry_notional = abs(t.get('qty', 0) * t.get('entry_price', 1))
            if entry_notional > 0:
                returns.append(pnl / entry_notional)
        
        if returns:
            avg_trade_return = sum(returns) / len(returns)

    return {
        "start_equity": start_eq,
        "end_equity": end_eq,
        "total_return": total_return,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe": sharpe,
        "trades_count": trades_count,
        "win_rate": win_rate,
        "avg_trade_return": avg_trade_return,
        "exposure_time": exposure_time,
        "start_ts": equity_curve.index[0].isoformat(),
        "end_ts": equity_curve.index[-1].isoformat()
    }

def filter_by_split(equity_curve: pd.DataFrame, trades: list, split: str) -> tuple:
    """
    Filter equity curve and trades by OOS split.
    """
    splits = {
        "TRAIN": ("2020-01-01", "2022-12-31"),
        "VAL":   ("2023-01-01", "2023-12-31"),
        "OOS":   ("2024-01-01", "2099-12-31")
    }
    
    if split not in splits:
        return equity_curve, trades
        
    start_str, end_str = splits[split]
    
    # Handle timezone aware vs naive
    if equity_curve.index.tz:
        start_dt = pd.Timestamp(start_str).tz_localize("UTC").tz_convert(equity_curve.index.tz)
        end_dt = (pd.Timestamp(end_str) + pd.Timedelta(days=1)).tz_localize("UTC").tz_convert(equity_curve.index.tz) - pd.Timedelta(seconds=1)
    else:
        start_dt = pd.Timestamp(start_str)
        end_dt = pd.Timestamp(end_str) + pd.Timedelta(hours=23, minutes=59, seconds=59)
    
    sub_curve = equity_curve[(equity_curve.index >= start_dt) & (equity_curve.index <= end_dt)]
    
    full_trades_df = pd.DataFrame(trades)
    if not full_trades_df.empty and 'ts_entry' in full_trades_df.columns:
         # Standardizing to ts_entry for C15
         full_trades_df['ts_entry'] = pd.to_datetime(full_trades_df['ts_entry'])
         sub_trades_df = full_trades_df[(full_trades_df['ts_entry'] >= start_dt) & (full_trades_df['ts_entry'] <= end_dt)]
         sub_trades = sub_trades_df.to_dict('records')
    else:
        sub_trades = []
        
    return sub_curve, sub_trades
