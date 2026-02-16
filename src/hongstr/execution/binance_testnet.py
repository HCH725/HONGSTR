import requests
import hashlib
import hmac
import time
import pandas as pd
from typing import List, Optional
from hongstr.execution.broker import AbstractBroker
from hongstr.execution.models import OrderRequest, OrderResult, Position
from hongstr.config import BINANCE_TESTNET_BASE_URL, BINANCE_API_KEY, BINANCE_SECRET_KEY, OFFLINE_MODE
from hongstr.alerts.telegram import send_alert

class BinanceFuturesTestnetBroker(AbstractBroker):
    def __init__(self):
        self.base_url = BINANCE_TESTNET_BASE_URL
        self.key = BINANCE_API_KEY
        self.base_url = BINANCE_TESTNET_BASE_URL
        self.key = BINANCE_API_KEY
        self.secret = BINANCE_SECRET_KEY
        self._margin_checked = set()

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

        endpoint = "/fapi/v1/order"
        
        # Map fields
        # Hedge mode: needs positionSide.
        # OrderRequest.side = BUY/SELL
        # OrderRequest has NO positionSide? We need to infer from side/intent?
        # NO, C5 requirement: "Hedge mode: long/short tracked independently"
        # Since we are automating strategies, usually we map Strategy 'LONG' signal to 'LONG' position side.
        # BUT OrderRequest is just BUY/SELL. 
        # Broker needs to know if this is Opening LONG, Closing LONG, Opening SHORT, Closing SHORT.
        # Let's rely on 'extra' or convention.
        # Convention: Strategies output LONG/SHORT direction.
        # Entry LONG: side=BUY, positionSide=LONG
        # Exit LONG: side=SELL, positionSide=LONG (reduceOnly=True usually, but strictly positionSide must match)
        
        # We need to enhance OrderRequest or Executor logic to pass positionSide.
        # Use order.extra['positionSide'] if present, else default?
        
        position_side = order.extra.get('positionSide', 'BOTH') if order.extra else 'BOTH'
        
        params = {
            "symbol": order.symbol,
            "side": order.side,
            "type": order.order_type,
            "quantity": order.qty,
            "positionSide": position_side 
        }
        
        if order.price:
            params["price"] = order.price
            params["timeInForce"] = "GTC"
            
        if order.reduce_only:
             # In hedge mode, reduceOnly param is NOT valid. You must use closePosition or proper side logic.
             # Actually for LIMIT orders in Hedge Mode, you just place opposite side order on same positionSide.
             # It acts as reduce if net position is closed.
             # Binance API: "reduceOnly" is True or False. valid in One-way.
             # In Hedge Mode: reduceOnly is not sent. 
             # WE MUST KNOW IF WE ARE IN HEDGE MODE. 
             # Spec says: "Hedge mode: long/short tracked independently".
             # So we assume Hedge Mode is ON.
             # Thus, do NOT send reduceOnly=True. Send side=SELL, positionSide=LONG to close long.
             pass
        else:
             # Not reduce only
             pass

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
                 return OrderResult("err", "REJECTED", 0, 0, pd.Timestamp.now(), error=r.text)
        except Exception as e:
            return OrderResult("err", "ERROR", 0, 0, pd.Timestamp.now(), error=str(e))

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
