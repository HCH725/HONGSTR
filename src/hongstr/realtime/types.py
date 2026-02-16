from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional

class StreamType(str, Enum):
    AGG_TRADE = "aggTrade"
    KLINE = "kline"

class KlineInterval(str, Enum):
    ONE_MINUTE = "1m"
    THREE_MINUTES = "3m"
    FIVE_MINUTES = "5m"
    FIFTEEN_MINUTES = "15m"
    THIRTY_MINUTES = "30m"
    ONE_HOUR = "1h"
    TWO_HOURS = "2h"
    FOUR_HOURS = "4h"
    SIX_HOURS = "6h"
    EIGHT_HOURS = "8h"
    TWELVE_HOURS = "12h"
    ONE_DAY = "1d"
    THREE_DAYS = "3d"
    ONE_WEEK = "1w"
    ONE_MONTH = "1M"

@dataclass
class WSConfig:
    symbols: List[str]
    intervals: List[KlineInterval]
    output_dir: str
    ws_base_url: str = "wss://stream.binance.com:9443/stream"
    run_seconds: int = 30
    log_path: str = "logs/realtime.log"

@dataclass
class AggTradeEvent:
    event_type: str
    event_time: int
    symbol: str
    agg_trade_id: int
    price: float
    quantity: float
    first_trade_id: int
    last_trade_id: int
    trade_time: int
    is_buyer_maker: bool

@dataclass
class KlineData:
    start_time: int
    close_time: int
    symbol: str
    interval: str
    first_trade_id: int
    last_trade_id: int
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    base_asset_volume: float
    number_of_trades: int
    is_closed: bool
    quote_asset_volume: float
    taker_buy_base_asset_volume: float
    taker_buy_quote_asset_volume: float

@dataclass
class KlineEvent:
    event_type: str
    event_time: int
    symbol: str
    kline: KlineData
