import time
from hongstr.execution.broker import AbstractBroker
from hongstr.execution.models import Position
from hongstr.alerts.telegram import send_alert
from hongstr.config import OFFLINE_MODE

class Reconciler:
    def __init__(self, broker: AbstractBroker):
        self.broker = broker
        
    def run_once(self):
        if OFFLINE_MODE: return
        
        # 1. Check Orphans
        symbol = "BTCUSDT"
        
        pos = self.broker.get_position(symbol)
        orders = self.broker.get_open_orders(symbol)
        
        # print(f"Reconciler: {symbol} Pos={pos.side} Orders={len(orders)}")
        
        if pos.side == 'NONE' and len(orders) > 0:
            # Gate-3: Manual close detected (Orphan brackets)
            # Log event
            print(f"Reconciler: MANUAL CLOSE DETECTED for {symbol}. cancelling {len(orders)} orphan orders.")
            
            # Alert
            send_alert(f"Manual Close / Orphan Brackets detected for {symbol}. Cancelling {len(orders)} orders.", "WARN")
            
            for o in orders:
                self.broker.cancel_order(symbol, o['orderId'])
                
        # 2. Missing Bracket
        # If position exists, expect 2 orders (TP/SL)? Or at least 1?
        if pos.side != 'NONE':
            if len(orders) == 0:
                send_alert(f"Position {symbol} exists but NO open orders (Missing Bracket).", "CRIT")
            elif len(orders) < 2:
                 # Partial bracket or just SL?
                 pass
