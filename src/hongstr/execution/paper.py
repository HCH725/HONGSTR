import pandas as pd
import json
import os
import uuid
from typing import List, Dict
from hongstr.execution.broker import AbstractBroker
from hongstr.execution.models import OrderRequest, OrderResult, Position
from hongstr.config import DATA_DIR, OFFLINE_MODE
from hongstr.semantics.core import SemanticsV1
from hongstr.alerts.telegram import send_alert

class PaperBroker(AbstractBroker):
    def __init__(self, semantics: SemanticsV1):
        self.semantics = semantics
        self.positions: Dict[str, Position] = {} # symbol -> Position
        self.open_orders: List[Dict] = []
        self.balance = 100000.0
        self.paper_dir = DATA_DIR / "paper"
        os.makedirs(self.paper_dir, exist_ok=True)
        self._load_state()

    def _load_state(self):
        # Load simplistic state if exists
        pos_path = self.paper_dir / "positions.json"
        if pos_path.exists():
            try:
                with open(pos_path, 'r') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.positions[k] = Position(**v)
            except:
                pass

    def _save_state(self):
        pos_path = self.paper_dir / "positions.json"
        with open(pos_path, 'w') as f:
            data = {k: v.__dict__ for k, v in self.positions.items()}
            # Convert timestamp to str
            for k in data:
                if data[k]['timestamp']:
                    data[k]['timestamp'] = str(data[k]['timestamp'])
            json.dump(data, f, indent=2)

    def ping(self) -> bool:
        return True

    def get_account_balance(self) -> float:
        return self.balance

    def place_order(self, order: OrderRequest) -> OrderResult:
        if OFFLINE_MODE:
            send_alert("OFFLINE_MODE blocked place_order", "WARN")
            return OrderResult("err", "REJECTED", 0, 0, pd.Timestamp.now(), "OFFLINE_MODE")

        # Handle LIMIT / STOP -> Queue ONLY
        if order.order_type in ['LIMIT', 'STOP', 'STOP_MARKET', 'TAKE_PROFIT', 'TAKE_PROFIT_MARKET']:
             order_id = str(uuid.uuid4())
             self.open_orders.append({
                 'order_id': order_id,
                 'symbol': order.symbol,
                 'side': order.side,
                 'price': order.price,
                 'qty': order.qty,
                 'reduce_only': order.reduce_only
             })
             return OrderResult(order_id, "NEW", 0.0, 0.0, pd.Timestamp.now())

        # Handle MARKET -> Fill Immediately
        # Simulate Fill
        exec_price = 10000.0 # Fallback mock
        if order.price: exec_price = order.price # If provided (paper sim)

        # Update Position
        pos = self.positions.get(order.symbol, Position(order.symbol, 'NONE', 0.0, 0.0))
        
        # ReduceOnly check
        if order.reduce_only:
            if pos.side == 'NONE':
                return OrderResult("err", "REJECTED", 0, 0, pd.Timestamp.now(), "ReduceOnly but no position")
            if (pos.side == 'LONG' and order.side == 'BUY') or (pos.side == 'SHORT' and order.side == 'SELL'):
                 return OrderResult("err", "REJECTED", 0, 0, pd.Timestamp.now(), "ReduceOnly wrong side")
            # Cap qty
            if order.qty > pos.amt:
                order.qty = pos.amt 

        # Valid fill
        filled_qty = order.qty
        
        # Update Pos Logic (Simple Netting)
        new_amt = pos.amt
        new_side = pos.side
        new_entry = pos.entry_price

        if order.side == 'BUY':
            if pos.side == 'LONG':
                total_val = pos.amt * pos.entry_price + filled_qty * exec_price
                new_amt += filled_qty
                new_entry = total_val / new_amt if new_amt > 0 else 0
            elif pos.side == 'SHORT':
                new_amt -= filled_qty
                if new_amt < 0:
                    new_side = 'LONG'
                    new_amt = abs(new_amt)
                    new_entry = exec_price
                elif new_amt == 0:
                    new_side = 'NONE'
                    new_entry = 0.0
            else: # NONE
                new_side = 'LONG'
                new_amt = filled_qty
                new_entry = exec_price
        else: # SELL
            if pos.side == 'SHORT':
                total_val = pos.amt * pos.entry_price + filled_qty * exec_price
                new_amt += filled_qty
                new_entry = total_val / new_amt if new_amt > 0 else 0
            elif pos.side == 'LONG':
                new_amt -= filled_qty
                if new_amt < 0:
                    new_side = 'SHORT'
                    new_amt = abs(new_amt)
                    new_entry = exec_price
                elif new_amt == 0:
                    new_side = 'NONE'
                    new_entry = 0.0
            else: # NONE
                new_side = 'SHORT'
                new_amt = filled_qty
                new_entry = exec_price
        
        self.positions[order.symbol] = Position(order.symbol, new_side, new_amt, new_entry, 0.0, pd.Timestamp.now())
        self._save_state()
        
        return OrderResult(
            str(uuid.uuid4()),
            "FILLED",
            exec_price,
            filled_qty,
            pd.Timestamp.now()
        )

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        if OFFLINE_MODE: return False
        initial_len = len(self.open_orders)
        self.open_orders = [o for o in self.open_orders if o['order_id'] != order_id]
        return len(self.open_orders) < initial_len

    def get_open_orders(self, symbol: str) -> List[dict]:
        # Return dict matching Binance keys partially for compatibility
        return [
            {
                "orderId": o['order_id'],
                "symbol": o['symbol'],
                "side": o['side'],
                "price": o['price'],
                "origQty": o['qty'],
                "reduceOnly": o['reduce_only']
            }
            for o in self.open_orders if o['symbol'] == symbol
        ]

    def get_position(self, symbol: str) -> Position:
        return self.positions.get(symbol, Position(symbol, 'NONE', 0.0, 0.0))
