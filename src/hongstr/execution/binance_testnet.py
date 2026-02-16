import requests
import hashlib
import hmac
import time
import pandas as pd
from typing import List, Optional
from hongstr.execution.broker import AbstractBroker
from hongstr.execution.models import OrderRequest, OrderResult, Position
from hongstr.config import (
    BINANCE_TESTNET_BASE_URL, 
    BINANCE_API_KEY, 
    BINANCE_SECRET_KEY, 
    OFFLINE_MODE,
    BINANCE_HEDGE_MODE
)
from hongstr.execution.exchange_filters import ExchangeFilters
from hongstr.alerts.telegram import send_alert

class BinanceFuturesTestnetBroker(AbstractBroker):
    def __init__(self, semantics: str = "Testnet"):
        self.base_url = BINANCE_TESTNET_BASE_URL
        self.key = BINANCE_API_KEY
        self.secret = BINANCE_SECRET_KEY
        self.semantics = semantics
        self._margin_checked = set()
        self.filters = ExchangeFilters()

    def _ensure_isolated_margin(self, symbol: str):
        if OFFLINE_MODE: return
        if symbol in self._margin_checked: return

        # Check margin type
        endpoint = "/fapi/v1/positionRisk"
        try:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign({"symbol": symbol}))
            if r.status_code == 200:
                data = r.json()
                # data is list. Check all have marginType='ISOLATED'
                for p in data:
                    if p.get('marginType') != 'isolated':
                        send_alert(f"CRIT: Symbol {symbol} is NOT ISOLATED margin. Blocking.", "CRIT")
                        raise RuntimeError(f"Margin Mode Mismatch: {p.get('marginType')}")
                self._margin_checked.add(symbol)
        except Exception as e:
            if "Margin Mode Mismatch" in str(e): raise e
            send_alert(f"Margin check failed: {e}", "WARN")

    def _sign(self, params: dict) -> dict:
        params['timestamp'] = int(time.time() * 1000)
        query = '&'.join([f"{k}={v}" for k,v in params.items()])
        sig = hmac.new(self.secret.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = sig
        return params

    def _headers(self):
        return {"X-MBX-APIKEY": self.key}

    def ping(self) -> bool:
        if OFFLINE_MODE: return False
        try:
            r = requests.get(f"{self.base_url}/fapi/v1/ping", timeout=3)
            return r.status_code == 200
        except:
            return False

    def get_account_balance(self) -> float:
        if OFFLINE_MODE: return 0.0
        try:
            r = requests.get(f"{self.base_url}/fapi/v2/account", headers=self._headers(), params=self._sign({}))
            if r.status_code == 200:
                data = r.json()
                return float(data['availableBalance']) # Simple available
            return 0.0
        except Exception as e:
            send_alert(f"Binance balance check failed: {e}", "WARN")
            return 0.0

    def place_order(self, order: OrderRequest) -> OrderResult:
        if OFFLINE_MODE:
            send_alert("OFFLINE_MODE blocked place_order (Binance)", "WARN")
            raise RuntimeError("OFFLINE_MODE")

        self._ensure_isolated_margin(order.symbol)
        
        # Apply Filters
        qty = self.filters.round_qty(order.symbol, order.qty)
        price = self.filters.round_price(order.symbol, order.price) if order.price else None

        endpoint = "/fapi/v1/order"
        
        # Determine Position Side
        # In Hedge Mode, closing requires explicit positionSide matching the position being closed.
        # Opening requires explicit positionSide (LONG for Buy, SHORT for Sell usually).
        # We rely on 'extra' or default logic.
        
        pos_side = 'BOTH' # Default for One-way
        if BINANCE_HEDGE_MODE:
            if order.extra and 'positionSide' in order.extra:
                pos_side = order.extra['positionSide']
            else:
                # Fallback: BUY -> LONG, SELL -> SHORT? 
                # Risky if closing. But Executor should have set extra.
                pos_side = 'LONG' if order.side == 'BUY' else 'SHORT'
        
        params = {
            "symbol": order.symbol,
            "side": order.side,
            "type": order.order_type,
            "quantity": qty,
            "positionSide": pos_side
        }
        
        if price:
            params["price"] = price
            params["timeInForce"] = "GTC"
            
        # ReduceOnly logic
        if not BINANCE_HEDGE_MODE and order.reduce_only:
            params["reduceOnly"] = "true"
        # In Hedge Mode, reduceOnly is implied by closing opposite side.

        # If client_order_id
        if order.client_order_id:
            params["newClientOrderId"] = order.client_order_id

        try:
            r = requests.post(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign(params))
            if r.status_code == 200:
                data = r.json()
                return OrderResult(
                    str(data['orderId']),
                    data['status'],
                    float(data.get('avgPrice', 0.0)),
                    float(data.get('executedQty', 0.0)),
                    pd.Timestamp.now()
                )
            else:
                err = r.json()
                return OrderResult("", "EXCHANGE_REJECTED", 0.0, 0.0, pd.Timestamp.now(), error=f"{err.get('code')} {err.get('msg')}")
        except Exception as e:
            return OrderResult("", "EXCHANGE_ERROR", 0.0, 0.0, pd.Timestamp.now(), error=str(e))

    def cancel_order(self, symbol: str, order_id: str) -> bool:
        if OFFLINE_MODE: return False
        endpoint = "/fapi/v1/order"
        params = {"symbol": symbol, "orderId": order_id}
        try:
             r = requests.delete(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign(params))
             return r.status_code == 200
        except:
             return False

    def get_open_orders(self, symbol: str) -> List[dict]:
        if OFFLINE_MODE: return []
        endpoint = "/fapi/v1/openOrders"
        try:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign({"symbol": symbol}))
            if r.status_code == 200:
                return r.json()
            return []
        except:
            return []

    def get_position(self, symbol: str) -> Position:
        if OFFLINE_MODE: return Position(symbol, 'NONE', 0, 0)
        endpoint = "/fapi/v2/positionRisk"
        # We need to fetch all and filter by symbol
        try:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign({"symbol": symbol}))
            if r.status_code == 200:
                data = r.json()
                # data is list (hedge mode -> 2 entries: LONG and SHORT)
                # We need to aggregate or return specific?
                # AbstractBroker.get_position returns 'Position'. 
                # If we have both long and short, abstract model 'side' is limited.
                # However, HONG Strategy Policy: "isolated portfolio". Usually 1 direction at a time per strategy.
                # But Broker needs to handle what's there.
                # Let's return the largest position or default NONE.
                # Ideally, we should support returning list of positions. But interface is simple.
                # Phase 0: HONG trend biased, likely 1 dir.
                
                long_pos = next((p for p in data if p['positionSide'] == 'LONG'), None)
                short_pos = next((p for p in data if p['positionSide'] == 'SHORT'), None)
                
                l_amt = float(long_pos['positionAmt']) if long_pos else 0
                s_amt = abs(float(short_pos['positionAmt'])) if short_pos else 0
                
                if l_amt > 0:
                    return Position(symbol, 'LONG', l_amt, float(long_pos['entryPrice']))
                elif s_amt > 0:
                    return Position(symbol, 'SHORT', s_amt, float(short_pos['entryPrice']))
                
                return Position(symbol, 'NONE', 0, 0)
            return Position(symbol, 'NONE', 0, 0)
        except:
            return Position(symbol, 'NONE', 0, 0)

    def get_all_positions(self) -> List[Position]:
        if OFFLINE_MODE: return []
        endpoint = "/fapi/v2/positionRisk"
        try:
            r = requests.get(f"{self.base_url}{endpoint}", headers=self._headers(), params=self._sign({}))
            if r.status_code == 200:
                data = r.json()
                # Group by symbol
                pos_map = {}
                for p in data:
                    sym = p['symbol']
                    amt = float(p['positionAmt'])
                    if abs(amt) > 0:
                         # Decide side
                         side = 'LONG' if amt > 0 else 'SHORT'
                         # If hedge mode, we might see 2 entries per symbol. 
                         # Logic similar to get_position but applied to all.
                         # Simplified: Just grab what's active.
                         pos_map[sym] = Position(sym, side, abs(amt), float(p['entryPrice']))
                return list(pos_map.values())
            return []
        except Exception as e:
            send_alert(f"Binance get_all_positions failed: {e}", "WARN")
            return []
