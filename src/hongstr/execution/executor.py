import pandas as pd
import uuid
import os
import json
from typing import Optional
from hongstr.execution.models import SignalEvent, OrderRequest, OrderResult, BracketPlan, Position
from hongstr.execution.broker import AbstractBroker
from hongstr.selection.artifact import load_selection_artifact
from hongstr.config import EXECUTION_MODE, OFFLINE_MODE, MAX_CONCURRENT_POSITIONS, POSITION_SIZE_PCT_DEFAULT, PORTFOLIO_ID
from hongstr.alerts.telegram import send_alert
from hongstr.selection.selector import Selector
from hongstr.execution.risk import RiskManager
from hongstr.execution.exchange_filters import ExchangeFilters

class ExecutionEngine:
    def __init__(self, broker: AbstractBroker):
        self.broker = broker
        self.selector = Selector({}) 
        self.state_dir = "data/state"
        os.makedirs(self.state_dir, exist_ok=True)
        self.risk_manager = RiskManager()
        self.filters = ExchangeFilters()

    def load_selection(self):
        try:
            # Gate-1: FAIL-CLOSED validation
            return load_selection_artifact(
                self.selector.DEFAULT_SELECTION_PATH, 
                expected_portfolio_id=PORTFOLIO_ID
            )
        except Exception as e:
            send_alert(f"CRIT: Validation Failed for selection artifact: {e}", "CRIT")
            # If blocking execution, we return None, and execute_signal returns.
            # In loop runner, we might want to exit? 
            # StrategyRunner calls execute_signal. 
            # Returning None stops this signal.
            return None

    def _persist_execution(self, event_type: str, data: dict):
        # types: "INTENT", "RESULT"
        # file: data/state/execution_{type}.jsonl
        try:
            filename = f"execution_{event_type.lower()}.jsonl"
            path = os.path.join(self.state_dir, filename)
            with open(path, 'a') as f:
                entry = data.copy()
                entry['ts'] = str(pd.Timestamp.now())
                f.write(json.dumps(entry, default=str) + "\n")
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            send_alert(f"Failed to persist execution: {e}", "WARN")

    def execute_signal(self, signal: SignalEvent):
        # Persist Intent
        self._persist_execution("INTENT", {"signal": signal.__dict__})

        if OFFLINE_MODE:
            send_alert(f"Signal ignored (OFFLINE): {signal.symbol}", "WARN")
            return

        # 1. Validate Signal
        selection_data = self.load_selection()
        if not selection_data:
            send_alert("Selection Artifact Missing/Invalid. Ignoring signal.", "WARN")
            self._persist_execution("SKIPPED", {"reason": "No Selection Artifact", "signal_id": str(signal.ts)})
            return
            
        # 2. Check Selection
        # selection_data is dict obeying selection_artifact_v1
        sel_dict = selection_data.get('selection', {})
        allowed_strategies = set()
        for k in sel_dict:
            allowed_strategies.update(sel_dict[k])
            
        is_selected = signal.strategy_id in allowed_strategies
        if not is_selected:
            send_alert(f"Strategy {signal.strategy_id} not selected. IGNORED.", "INFO")
            return

        # 3. Risk Checks (Direction / Opposite)
        # Check current position
        positions_list = self.broker.get_all_positions() 
        pos_dict = {p.symbol: p for p in positions_list}
        pos = pos_dict.get(signal.symbol, Position(signal.symbol, 'NONE', 0.0, 0.0))
        
        if pos.side != 'NONE':
            if (pos.side == 'LONG' and signal.direction == 'SHORT') or \
               (pos.side == 'SHORT' and signal.direction == 'LONG'):
                 # Opposite signal: Close current
                 send_alert(f"Opposite signal {signal.direction} vs {pos.side}. Closing...", "INFO")
                 self._close_position(signal.symbol, pos)
                 # Proceed to entry? Usually yes for FLIP.
                 # But for smoke test simplicity and safety, let's close first.
                 # Updated State: balance changes, position changes.
                 # For MVP C12, let's assume Close is enough for this tick or proceed if balance allows.
                 # We proceed.
            else:
                 # Same side, ignore
                 return
        
        # Entry Sizing
        balance = self.broker.get_account_balance()
        if balance <= 0:
             # logger.warning("Balance <= 0. Skipping.")
             return

        size_usd = balance * POSITION_SIZE_PCT_DEFAULT
        price = 100000.0 # Safety fallback
        if EXECUTION_MODE == 'B':
             pass # Use dummy
        
        qty = size_usd / price
        
        # Apply Filters Rounding
        qty = self.filters.round_qty(signal.symbol, qty)
        
        if qty <= 0: return

        # 4. Prepare Order & Risk Check
        side = 'BUY' if signal.direction == 'LONG' else 'SELL'
        position_side = 'LONG' if signal.direction == 'LONG' else 'SHORT'
        
        req = OrderRequest(
            symbol=signal.symbol,
            side=side,
            qty=qty,
            order_type='MARKET',
            price=price if EXECUTION_MODE=='B' else None, # Hint for paper
            extra={'positionSide': position_side}
        )
        
        # Risk Check
        risk_decision = self.risk_manager.evaluate(signal, req, pos_dict, balance)
        
        if not risk_decision.allowed:
            send_alert(f"Risk Reject: {risk_decision.reason}", "WARN")
            self._persist_execution("RESULT", {
                "signal": signal.__dict__,
                "order": req.__dict__,
                "decision": "REJECTED",
                "status": "REJECTED_RISK",
                "reason": risk_decision.reason,
                "details": risk_decision.details
            })
            return

        # 5. Place Entry
        res = self.broker.place_order(req)
        
        # Persist success with decision info
        res_data = {
            "order": req.__dict__, 
            "result": res.__dict__,
            "decision": "ALLOWED",
            "reason": "ALLOWED"
        }
        self._persist_execution("RESULT", res_data)
        
        if res.status == 'FILLED' or res.status == 'NEW': 
             send_alert(f"Entry {side} {signal.symbol} Executed @ {res.avg_price}", "INFO")
             # self._place_bracket(signal, res.avg_price, qty, position_side) # Bracket logic later
        else:
             send_alert(f"Entry Failed: {res.error}", "CRIT")

    def _place_bracket(self, signal, entry_price, qty, position_side):
        # Gate-2: Idempotency
        # Check existing orders for this symbol
        open_orders = self.broker.get_open_orders(signal.symbol)
        
        # We classify existing orders
        has_sl = False
        has_tp = False
        
        for o in open_orders:
            # Binance types: STOP_MARKET, TAKE_PROFIT_MARKET usually
            # Paper: STOP, TAKE_PROFIT
            # Reduced to common naming if broker normalizes, or check raw
            otype = o.get('type', '').upper()
            if otype in ['STOP', 'STOP_MARKET']:
                has_sl = True
            elif otype in ['TAKE_PROFIT', 'TAKE_PROFIT_MARKET']:
                has_tp = True
                
        if has_sl and has_tp:
            send_alert(f"Bracket already exists for {signal.symbol}. Skipping (Idempotency).", "INFO")
            return

        # TP/SL logic
        # Defaults
        tp_pct = 0.05
        sl_pct = 0.02
        
        if signal.direction == 'LONG':
            tp = entry_price * (1 + tp_pct)
            sl = entry_price * (1 - sl_pct)
            exit_side = 'SELL'
        else:
            tp = entry_price * (1 - tp_pct)
            sl = entry_price * (1 + sl_pct)
            exit_side = 'BUY'
            
        # SL First (Rule)
        if not has_sl:
            sl_req = OrderRequest(
                symbol=signal.symbol,
                side=exit_side,
                qty=qty,
                order_type='STOP', 
                price=sl,
                reduce_only=True,
                extra={'positionSide': position_side, 'stopPrice': sl}
            )
            
            sl_res = self.broker.place_order(sl_req)
            if sl_res.status not in ['NEW', 'FILLED']:
                send_alert(f"CRIT: SL Placement Failed for {signal.symbol}: {sl_res.error}", "CRIT")
                return # Stop bracket placement

        # TP Second
        if not has_tp:
            tp_req = OrderRequest(
                symbol=signal.symbol,
                side=exit_side,
                qty=qty,
                order_type='TAKE_PROFIT',
                price=tp,
                reduce_only=True,
                extra={'positionSide': position_side, 'stopPrice': tp}
            )
            
            tp_res = self.broker.place_order(tp_req)
            if tp_res.status not in ['NEW', 'FILLED']:
                 send_alert(f"WARN: TP Placement Failed for {signal.symbol}: {tp_res.error}", "WARN")

    def _close_position(self, symbol: str, pos: Position):
        # Enforce NO_POSITION check
        if pos.side == 'NONE' or pos.amt == 0:
            send_alert(f"Close requested for {symbol} but NO_POSITION. Skipped.", "WARN")
            self._persist_execution("RESULT", {
                "decision": "SKIPPED",
                "status": "NO_POSITION",
                "reason": "CLOSE_WITHOUT_POSITION",
                "symbol": symbol
            })
            return

        side = 'SELL' if pos.side == 'LONG' else 'BUY'
        # Close full amount
        qty = self.filters.round_qty(symbol, pos.amt)
        
        req = OrderRequest(
            symbol=symbol,
            side=side,
            qty=qty,
            order_type='MARKET',
            reduce_only=True,
            extra={'positionSide': pos.side}
        )
        res = self.broker.place_order(req)
        self._persist_execution("RESULT", {"action": "CLOSE", "result": res.__dict__})
        send_alert(f"Closed {pos.side} {symbol} @ {res.avg_price}", "INFO")
