import asyncio
import os
import logging
import sys
import pandas as pd
from hongstr.config import (
    BINANCE_TESTNET_BASE_URL, BINANCE_API_KEY, BINANCE_SECRET_KEY, 
    BINANCE_HEDGE_MODE, SMOKE_NOTIONAL_USD, SMOKE_RUNTIME_SEC,
    DEFAULT_TESTNET_SYMBOL, ENABLE_BRACKETS
)
from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
from hongstr.execution.models import OrderRequest, SignalEvent
from hongstr.execution.exchange_filters import ExchangeFilters
from hongstr.execution.executor import ExecutionEngine

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("smoke_c13")

async def run_smoke():
    logger.info("--- Starting C13 Testnet Live Smoke ---")
    
    # 1. Broker & Filters
    broker = BinanceFuturesTestnetBroker(semantics="Testnet")
    filters = ExchangeFilters()
    
    symbol = DEFAULT_TESTNET_SYMBOL
    
    # Check Connectivity
    if not broker.ping():
        logger.error("Broker Ping Failed. Check Network/Url.")
        sys.exit(1)
        
    logger.info(f"Broker Ping OK. Symbol: {symbol}")
    
    # Check Balance
    balance = broker.get_account_balance()
    logger.info(f"Balance: {balance} USDT")
    
    if balance < 10.0:
        logger.error("Insufficient Balance for Smoke Test.")
        sys.exit(1)
        
    # 2. Market Order (Long)
    # Calculate Qty
    # We need price. Broker doesn't have get_price(). Use Filters? No.
    # We'll use a dummy price or try to fetch from exchange if broker has method.
    # Broker doesn't have get_price.
    # We can use requests directly for simple ticker or assume safe buffer.
    # Better: Add get_symbol_price to broker or just use requests here.
    import requests
    try:
        r = requests.get(f"{BINANCE_TESTNET_BASE_URL}/fapi/v1/ticker/price", params={"symbol": symbol})
        price = float(r.json()['price'])
        logger.info(f"Current Price {symbol}: {price}")
    except Exception as e:
        logger.error(f"Failed to fetch price: {e}")
        sys.exit(1)
        
    notional = SMOKE_NOTIONAL_USD
    raw_qty = notional / price
    qty = filters.round_qty(symbol, raw_qty)
    
    logger.info(f"Target Notional: ${notional}, Price: {price}, Qty: {qty}")
    
    if qty <= 0:
        logger.error("Calculated Qty is 0. Increase SMOKE_NOTIONAL_USD.")
        sys.exit(1)
        
    # Place Order
    logger.info("Placing MARKET BUY...")
    req = OrderRequest(
        symbol=symbol,
        side="BUY",
        qty=qty,
        order_type="MARKET",
        extra={"positionSide": "LONG"} if BINANCE_HEDGE_MODE else {}
    )
    
    res = broker.place_order(req)
    logger.info(f"Entry Result: {res.status} {res.error if res.error else ''}")
    
    if res.status != 'FILLED' and res.status != 'NEW':
        logger.error("Entry Failed. Aborting.")
        sys.exit(1)
        
    # 3. Brackets (if enabled)
    if ENABLE_BRACKETS:
        logger.info("Placing Brackets (ReduceOnly)...")
        # SL
        sl_price = price * 0.995
        sl_price = filters.round_price(symbol, sl_price)
        sl_req = OrderRequest(
            symbol=symbol,
            side="SELL",
            qty=qty,
            order_type="STOP_MARKET",
            price=sl_price,
            reduce_only=True,
            extra={"positionSide": "LONG", "stopPrice": sl_price} if BINANCE_HEDGE_MODE else {"stopPrice": sl_price}
        )
        sl_res = broker.place_order(sl_req)
        logger.info(f"SL Result: {sl_res.status} {sl_res.error if sl_res.error else ''}")
        
    # 4. Wait
    logger.info(f"Waiting {SMOKE_RUNTIME_SEC}s...")
    await asyncio.sleep(SMOKE_RUNTIME_SEC)
    
    # 5. Cleanup
    logger.info("Cleaning up...")
    
    # Cancel Orders
    orders = broker.get_open_orders(symbol)
    for o in orders:
        broker.cancel_order(symbol, o['orderId'])
        logger.info(f"Cancelled {o['orderId']}")
        
    # Close Position
    pos = broker.get_position(symbol)
    if pos.side != 'NONE' and pos.amt > 0:
        logger.info(f"Closing Position {pos.side} {pos.amt}...")
        close_req = OrderRequest(
            symbol=symbol,
            side="SELL", # Assuming Long
            qty=filters.round_qty(symbol, pos.amt),
            order_type="MARKET",
            reduce_only=True,
            extra={"positionSide": "LONG"} if BINANCE_HEDGE_MODE else {}
        )
        c_res = broker.place_order(close_req)
        logger.info(f"Close Result: {c_res.status}")
        
    logger.info("--- Smoke Test Complete ---")

if __name__ == "__main__":
    asyncio.run(run_smoke())
