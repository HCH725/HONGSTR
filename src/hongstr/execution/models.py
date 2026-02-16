from dataclasses import dataclass
from typing import Optional
import pandas as pd

@dataclass
class SignalEvent:
    ts: pd.Timestamp
    symbol: str
    portfolio_id: str
    strategy_id: str
    direction: str  # 'LONG', 'SHORT' (FLAT ignored by executor usually)
    timeframe: str
    regime: str
    confidence: float = 1.0

@dataclass
class OrderRequest:
    symbol: str
    side: str # 'BUY', 'SELL'
    qty: float
    order_type: str # 'MARKET', 'LIMIT'
    price: Optional[float] = None
    reduce_only: bool = False
    client_order_id: Optional[str] = None
    extra: Optional[dict] = None

@dataclass
class OrderResult:
    exchange_order_id: str
    status: str # 'FILLED', 'NEW', 'CANCELED', 'REJECTED'
    avg_price: float
    filled_qty: float
    ts: pd.Timestamp
    error: Optional[str] = None

@dataclass
class Position:
    symbol: str
    side: str # 'LONG', 'SHORT', 'NONE'
    amt: float
    entry_price: float
    unrealized_pnl: float = 0.0
    timestamp: Optional[pd.Timestamp] = None

@dataclass
class BracketPlan:
    entry_request: OrderRequest
    tp_price: float
    sl_price: float
