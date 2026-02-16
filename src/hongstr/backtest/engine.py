import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
from hongstr.semantics.core import SemanticsV1
from hongstr.backtest.metrics import calc_metrics, filter_by_split
from hongstr.config import TIMEZONE

class BacktestEngine:
    def __init__(self, semantics: SemanticsV1, data: pd.DataFrame, initial_capital: float = 10000.0):
        """
        data: DataFrame with OHLCV, indexed by datetime (Asia/Taipei aware preferably).
        """
        self.semantics = semantics
        self.data = data
        self.capital = initial_capital
        self.position = 0.0 # Signed size (positive=long, negative=short)
        self.entry_price = 0.0
        self.equity = initial_capital
        
        self.trades = []
        self.equity_curve = []
        
    def run(self, strategy_stub=None):
        """
        Main loop.
        strategy_stub: function(row) -> signal ('BUY', 'SELL', 'EXIT')
        """
        print(f"Starting Backtest with Semantics {self.semantics.version}...")
        
        # Ensure index is sorted
        df = self.data.sort_index()
        
        for ts, row in df.iterrows():
            # 1. Funding Logic
            # Delegate schedule check to Semantics Layer (Source of Truth)
            if self.semantics.is_funding_timestamp(ts):
                self._apply_funding(row['close'])
            
            # 2. Strategy Signal
            signal = None
            if strategy_stub:
                signal = strategy_stub(row)
            
            # 3. Execution (Market Orders)
            if signal == 'BUY':
                self._open_position(ts, row['close'], 1.0, 'LONG') # Fixed 1.0 unit for v1
            elif signal == 'SELL':
                self._open_position(ts, row['close'], 1.0, 'SHORT')
            elif signal == 'EXIT':
                self._close_position(ts, row['close'])
                
            # 4. TP/SL check (Bracket)
            # Only if position exists
            if self.position != 0:
                self._check_bracket(ts, row['high'], row['low'])
            
            # 5. Mark to Market
            self._update_equity(row['close'])
            self.equity_curve.append({'time': ts, 'equity': self.equity})

        # Finalize
        self.equity_df = pd.DataFrame(self.equity_curve).set_index('time')
        return self._generate_report()

    def _apply_funding(self, price):
        if self.position == 0:
            return
        # Dummy Funding Rate (0.01% per interval default simulation)
        rate = 0.0001 
        notional = self.position * price
        funding_pnl = self.semantics.calc_funding(notional, rate)
        self.capital += funding_pnl
        # Note: In real life, deducted from balance. Here capital tracks realized + cash.

    def _open_position(self, ts, price, size, side):
        if self.position != 0:
            return # Simple mode: one pos at a time
            
        # Slippage
        exec_price = self.semantics.apply_slippage(price, 'BUY' if side == 'LONG' else 'SELL')
        
        # Fee
        notional = size * exec_price
        fee = self.semantics.calc_fee(notional)
        
        self.position = size if side == 'LONG' else -size
        self.entry_price = exec_price
        self.capital -= fee
        
        self.trades.append({
            'entry_time': ts,
            'entry_price': exec_price,
            'size': self.position,
            'side': side,
            'fee': fee
        })

    def _close_position(self, ts, price):
        if self.position == 0:
            return
            
        side = 'SELL' if self.position > 0 else 'BUY'
        exec_price = self.semantics.apply_slippage(price, side)
        
        notional = abs(self.position) * exec_price
        fee = self.semantics.calc_fee(notional)
        
        # PnL
        pnl = (exec_price - self.entry_price) * self.position
        
        self.capital += pnl
        self.capital -= fee
        
        # Update last trade
        if self.trades:
            self.trades[-1]['exit_time'] = ts
            self.trades[-1]['exit_price'] = exec_price
            self.trades[-1]['pnl'] = pnl
            self.trades[-1]['exit_fee'] = fee
            self.trades[-1]['net_pnl'] = pnl - self.trades[-1]['fee'] - fee
            
        self.position = 0
        self.entry_price = 0

    def _check_bracket(self, ts, high, low):
        # Simulated TP/SL (e.g., 2% TP, 1% SL)
        if self.position == 0:
            return
            
        tp_pct = 0.02
        sl_pct = 0.01
        
        if self.position > 0: # Long
            tp_price = self.entry_price * (1 + tp_pct)
            sl_price = self.entry_price * (1 - sl_pct)
            
            # Conservative: check SL first? Or check overlap?
            # If Low <= SL, trigger SL
            if low <= sl_price:
                self._close_position(ts, sl_price) # Fill at SL
            elif high >= tp_price:
                self._close_position(ts, tp_price)
                
        elif self.position < 0: # Short
            tp_price = self.entry_price * (1 - tp_pct)
            sl_price = self.entry_price * (1 + sl_pct)
            
            if high >= sl_price:
                self._close_position(ts, sl_price)
            elif low <= tp_price:
                self._close_position(ts, tp_price)

    def _update_equity(self, current_price):
        unrealized = 0
        if self.position != 0:
            unrealized = (current_price - self.entry_price) * self.position
        self.equity = self.capital + unrealized

    def _generate_report(self):
        full_metrics = calc_metrics(self.equity_df, self.trades)
        
        splits = {}
        for split_name in ["TRAIN", "VAL", "OOS"]:
             sub_eq, sub_tr = filter_by_split(self.equity_df, self.trades, split_name)
             splits[split_name] = calc_metrics(sub_eq, sub_tr)
             
        return {
            "semantics_version": self.semantics.version,
            "full_metrics": full_metrics,
            "splits": splits,
            "trades": self.trades
        }
