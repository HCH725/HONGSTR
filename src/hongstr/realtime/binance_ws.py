import json
from typing import List, Dict, Any, Optional
from .types import AggTradeEvent, KlineEvent, KlineData

def build_stream_url(base_url: str, symbols: List[str], streams: List[str]) -> str:
    # streams e.g. ["aggTrade", "kline_1m"]
    # combined format: <base_url>?streams=<symbol1>@<stream1>/<symbol1>@<stream2>/...
    # BUT typically for combined streams it is <symbol>@<stream_type>
    # The requirement says: <symbol>@aggTrade, <symbol>@kline_<interval>
    
    combined_streams = []
    for s in symbols:
        s_lower = s.lower()
        for st in streams:
            combined_streams.append(f"{s_lower}@{st}")
            
    stream_string = "/".join(combined_streams)
    return f"{base_url}?streams={stream_string}"

def parse_aggtrade(data: Dict[str, Any]) -> AggTradeEvent:
    # "data": {
    #   "e": "aggTrade",  // Event type
    #   "E": 123456789,   // Event time
    #   "s": "BNBBTC",    // Symbol
    #   "a": 12345,       // Aggregate trade ID
    #   "p": "0.001",     // Price
    #   "q": "100",       // Quantity
    #   "f": 100,         // First trade ID
    #   "l": 105,         // Last trade ID
    #   "T": 123456785,   // Trade time
    #   "m": true,        // Is the buyer the market maker?
    #   "M": true         // Ignore
    # }
    return AggTradeEvent(
        event_type=data['e'],
        event_time=data['E'],
        symbol=data['s'],
        agg_trade_id=data['a'],
        price=float(data['p']),
        quantity=float(data['q']),
        first_trade_id=data['f'],
        last_trade_id=data['l'],
        trade_time=data['T'],
        is_buyer_maker=data['m']
    )

def parse_kline(data: Dict[str, Any]) -> KlineEvent:
    # "data": {
    #   "e": "kline",     // Event type
    #   "E": 123456789,   // Event time
    #   "s": "BNBBTC",    // Symbol
    #   "k": {
    #     "t": 123400000, // Kline start time
    #     "T": 123460000, // Kline close time
    #     "s": "BNBBTC",  // Symbol
    #     "i": "1m",      // Interval
    #     "f": 100,       // First trade ID
    #     "L": 200,       // Last trade ID
    #     "o": "0.0010",  // Open price
    #     "c": "0.0020",  // Close price
    #     "h": "0.0025",  // High price
    #     "l": "0.0015",  // Low price
    #     "v": "1000",    // Base asset volume
    #     "n": 100,       // Number of trades
    #     "x": false,     // Is this kline closed?
    #     "q": "1.0000",  // Quote asset volume
    #     "V": "500",     // Taker buy base asset volume
    #     "Q": "0.500",   // Taker buy quote asset volume
    #     "B": "123456"   // Ignore
    #   }
    # }
    k = data['k']
    kline_data = KlineData(
        start_time=k['t'],
        close_time=k['T'],
        symbol=k['s'],
        interval=k['i'],
        first_trade_id=k['f'],
        last_trade_id=k['L'],
        open_price=float(k['o']),
        close_price=float(k['c']),
        high_price=float(k['h']),
        low_price=float(k['l']),
        base_asset_volume=float(k['v']),
        number_of_trades=k['n'],
        is_closed=k['x'],
        quote_asset_volume=float(k['q']),
        taker_buy_base_asset_volume=float(k['V']),
        taker_buy_quote_asset_volume=float(k['Q'])
    )
    return KlineEvent(
        event_type=data['e'],
        event_time=data['E'],
        symbol=data['s'],
        kline=kline_data
    )
