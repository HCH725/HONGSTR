import pandas as pd
import numpy as np
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any

from hongstr.semantics.core import SemanticsV1
from hongstr.backtest.metrics import calc_metrics

class BacktestEngine:
    def __init__(
        self, 
        semantics: SemanticsV1, 
        data: pd.DataFrame, 
        initial_capital: float = 10000.0,
        size_notional_usd: float = 1000.0
    ):
        """
        data: DataFrame with OHLCV, indexed by datetime (UTC aware).
              Timestamp convention: Bar Start Time.
        """
        self.semantics = semantics
        self.data = data.sort_index()
        self.capital = initial_capital
        self.initial_capital = initial_capital
        self.size_notional_usd = size_notional_usd
        
        self.position_qty = 0.0 # Signed
        self.entry_price = 0.0
        self.equity = initial_capital
        
        self.trades = []
        self.equity_curve = []
        
        # Pending order for next_open fill
        self.pending_order: Optional[Dict[str, Any]] = None
        self.signals_count = 0

    def run(self, symbol: str, strategy_stub=None):
        """
        Main loop using next_open fill semantics.
        strategy_stub: function(row) -> direction string ("LONG", "SHORT", "FLAT", None)
        """
        df = self.data
        
        for i in range(len(df)):
            ts = df.index[i]
            row = df.iloc[i]
            
            # 1. Execute Pending Order (next_open)
            # A signal from Bar T is executed at Open of Bar T+1
            if self.pending_order:
                self._execute_pending(ts, row['open'], symbol)
            
            # 2. Update Equity (Mark to Market using high/low/close of current bar?)
            # Usually mark to market at bar close.
            self._update_equity(row['close'])
            self.equity_curve.append({
                'ts': ts.isoformat(),
                'equity': self.equity,
                'cash': self.capital,
                'position_notional': float(self.position_qty * row['close'])
            })

            # 3. Strategy Signal (on Bar T Close)
            if strategy_stub:
                # We pass the current row. If it's the last bar, we can't execute next_open.
                if i < len(df) - 1:
                    signal_dir = strategy_stub(row) 
                    if signal_dir:
                        self._process_signal(ts, signal_dir)

        # Finalize
        self.equity_df = pd.DataFrame(self.equity_curve)
        if not self.equity_df.empty:
            self.equity_df['ts'] = pd.to_datetime(self.equity_df['ts'])
            self.equity_df.set_index('ts', inplace=True)
        
        return self._generate_report(symbol, len(df))

    def _process_signal(self, ts, direction):
        """Queue an order for the next bar's open."""
        self.signals_count += 1
        # Simple Logic: Only queue if it changes position
        if direction == "LONG" and self.position_qty > 0: return
        if direction == "SHORT" and self.position_qty < 0: return
        if direction == "FLAT" and self.position_qty == 0: return
        
        self.pending_order = {
            "ts_signal": ts,
            "direction": direction,
            "signal_id": hashlib.md5(f"{ts}_{direction}".encode()).hexdigest()[:8]
        }

    def _execute_pending(self, ts, open_price, symbol):
        order = self.pending_order
        direction = order['direction']
        self.pending_order = None
        
        # 1. Close existing if needed
        if self.position_qty != 0:
            if direction == "FLAT" or (direction == "LONG" and self.position_qty < 0) or (direction == "SHORT" and self.position_qty > 0):
                self._close_position(ts, open_price, symbol, "Signal Flip" if direction != "FLAT" else "Signal Exit")
        
        # 2. Open new if needed
        if direction in ["LONG", "SHORT"]:
            side = direction # LONG or SHORT
            exec_price = self.semantics.apply_slippage(open_price, "BUY" if side == "LONG" else "SELL")
            
            qty = self.size_notional_usd / exec_price
            notional = qty * exec_price
            fee = self.semantics.calc_fee(notional)
            
            self.position_qty = qty if side == "LONG" else -qty
            self.entry_price = exec_price
            self.capital -= fee
            
            self.trades.append({
                "trade_id": str(uuid.uuid4())[:8],
                "signal_id": order['signal_id'],
                "ts_entry": ts.isoformat(),
                "ts_exit": None,
                "symbol": symbol,
                "side": side,
                "qty": float(self.position_qty),
                "entry_price": float(exec_price),
                "exit_price": None,
                "pnl": 0.0,
                "pnl_pct": 0.0,
                "fees": float(fee),
                "reason": "Entry"
            })

    def _close_position(self, ts, price, symbol, reason):
        if self.position_qty == 0: return
        
        side_close = "SELL" if self.position_qty > 0 else "BUY"
        exec_price = self.semantics.apply_slippage(price, side_close)
        
        notional = abs(self.position_qty) * exec_price
        fee = self.semantics.calc_fee(notional)
        
        pnl = (exec_price - self.entry_price) * self.position_qty
        pnl_pct = pnl / (abs(self.position_qty) * self.entry_price)
        
        self.capital += pnl
        self.capital -= fee
        
        if self.trades:
            t = self.trades[-1]
            t["ts_exit"] = ts.isoformat()
            t["exit_price"] = float(exec_price)
            t["pnl"] = float(pnl)
            t["pnl_pct"] = float(pnl_pct)
            t["fees"] += float(fee) 
            t["reason"] = reason

        self.position_qty = 0
        self.entry_price = 0

    def _update_equity(self, current_price):
        unrealized = 0
        if self.position_qty != 0:
            unrealized = (current_price - self.entry_price) * self.position_qty
        self.equity = self.capital + unrealized

    def _generate_report(self, symbol, total_bars):
        metrics = calc_metrics(self.equity_df, self.trades)
        
        report = {
            "symbol": symbol,
            "metrics": metrics,
            "counts": {
                "bars": total_bars,
                "signals": self.signals_count,
                "trades": len(self.trades)
            },
            "config": {
                "initial_capital": float(self.initial_capital),
                "size_notional_usd": float(self.size_notional_usd),
                "fill_mode": "next_open",
                "timestamp_convention": "bar_start_utc"
            },
            "equity_curve": self.equity_curve,
            "trades": self.trades
        }
        
        if len(self.trades) == 0:
            if self.signals_count == 0:
                report["no_trades_reason"] = "strategy_emitted_no_signals"
            elif total_bars < 2:
                report["no_trades_reason"] = "insufficient_bars_for_next_open"
            else:
                report["no_trades_reason"] = "signals_emitted_but_all_filtered_or_unfilled"
            
        return report
