import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set

import pandas as pd
import aiofiles

from ..config import REALTIME_OUT_DIR
from .types import Bar, SignalEvent, EngineConfig
from .resample import resample_bars
from .strategies.base import BaseStrategy
from .strategies.ma_cross import MACrossStrategy

logger = logging.getLogger(__name__)

class SignalEngine:
    def __init__(self, config: EngineConfig):
        self.config = config
        
        # Buffer: symbol -> deque of 1m bars
        self.bars_1m: Dict[str, Deque[Bar]] = defaultdict(lambda: deque(maxlen=config.max_bars))
        
        # State: latest emitted signal hash to dedup
        self._emitted_signals: Set[str] = set()
        
        self.strategies: List[BaseStrategy] = []
        self._load_strategies()
        
        # Persistence
        self.signal_file: Optional[aiofiles.threadpool.AsyncTextIOWrapper] = None
        self.current_date_str = ""
        self.processed_state: Dict[str, Dict[str, pd.Timestamp]] = defaultdict(dict)

    def _load_strategies(self):
        from ..config import STRATEGY_ENABLED, STRATEGY_LIST
        from .strategies.ma_cross import MACrossStrategy
        from .strategies.vwap_supertrend import VWAPSupertrendStrategy
        from .strategies.rsi_divergence import RSIDivergenceStrategy
        from .strategies.macd_divergence import MACDDivergenceStrategy

        if not STRATEGY_ENABLED:
            return

        for strat_name in STRATEGY_LIST:
            strat_name = strat_name.strip()
            if strat_name == "ma_cross":
                self.strategies.append(MACrossStrategy())
            elif strat_name == "vwap_supertrend":
                self.strategies.append(VWAPSupertrendStrategy())
            elif strat_name == "rsi_divergence":
                self.strategies.append(RSIDivergenceStrategy())
            elif strat_name == "macd_divergence":
                self.strategies.append(MACDDivergenceStrategy())

    def add_strategy(self, strategy: BaseStrategy):
        self.strategies.append(strategy)

    async def _init_storage(self):
        Path(self.config.state_root).mkdir(parents=True, exist_ok=True)
        Path(self.config.output_root).mkdir(parents=True, exist_ok=True)
        
        # Use single file for signals for now or rotating?
        # Runbook says "data/state/signal_events.jsonl"
        self.signal_file_path = Path(self.config.state_root) / "signal_events.jsonl"
        self.signal_file = await aiofiles.open(self.signal_file_path, mode='a', encoding='utf-8')

    async def _persist_signal(self, event: SignalEvent):
        if self.signal_file:
            await self.signal_file.write(json.dumps(event.to_dict()) + "\n")
            await self.signal_file.flush()
            
            # Also update "latest.json" in output_root
            latest_path = Path(self.config.output_root) / "latest.json"
            # Reading/Writing generic JSON asynchronously is tricky without full rewrite.
            # optimizing: skip for now or do sync write if low frequency.
            # Signals are low frequency (1h/4h). Sync write is fine.
            try:
                # We need to lock or atomic write properly, but let's just write to temp and rename
                 with open(str(latest_path) + ".tmp", "w") as f:
                     json.dump(event.to_dict(), f)
                 Path(str(latest_path) + ".tmp").replace(latest_path)
            except Exception as e:
                logger.error(f"Failed to update latest.json: {e}")

    def _process_jsonl_line(self, line: str):
        # Line format: {"ts_local": "...", "stream": "...", "data": {...}}
        try:
            record = json.loads(line)
            stream = record.get("stream", "")
            data = record.get("data", {})
            
            if "kline" in stream:
                # Process kline
                # kline data: {"e": "kline", "s": "BTCUSDT", "k": {"t": ..., "o": ..., "x": ...}}
                k = data.get("k", {})
                symbol = k.get("s")
                interval = k.get("i")
                is_closed = k.get("x")
                
                # We only ingest 1m klines into our base buffer
                if interval == "1m" and is_closed:
                    bar = Bar(
                        ts=pd.Timestamp(k['t'], unit='ms', tz='UTC'),
                        symbol=symbol,
                        open=float(k['o']),
                        high=float(k['h']),
                        low=float(k['l']),
                        close=float(k['c']),
                        volume=float(k['v']),
                        closed=True
                    )
                    self.bars_1m[symbol].append(bar)
                    self._on_new_1m_bar(symbol)
                    
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Error processing line: {e}")

    def _on_new_1m_bar(self, symbol: str):
        # Trigger resampling and strategy execution
        # Get all 1m bars for this symbol
        bars = list(self.bars_1m[symbol]) # Sort by TS? Deque should be sorted if ingested in order.
        
        task_list = []
        
        for tf in self.config.timeframes:
            # Resample
            resampled = resample_bars(bars, tf)
            
            if not resampled:
                continue
                
            last_bar = resampled[-1]
            last_ts = last_bar.ts
            
            # Check if we already processed this bar for this timeframe
            if self.processed_state[symbol].get(tf) == last_ts:
                continue
                
            self.processed_state[symbol][tf] = last_ts
            
            # Run strategies
            for strat in self.strategies:
                # Only if strat cares about this TF?
                # The logic in base.py says strat.on_bars(..., tf, ...).
                # Assuming strat handles filtering or we do it here.
                # Simplest: pass it to strat, let strat decide or pre-filter.
                # Optim: strict check using required_timeframes (but some might be dynamic).
                
                # Check requires
                # if tf in strat.required_timeframes:
                   # signal = strat.on_bars(symbol, tf, resampled)
                   # if signal: ...
                
                # Let's run it.
                try:
                    signal = strat.on_bars(symbol, tf, resampled)
                    if signal:
                        logger.info(f"SIGNAL: {signal}")
                        task_list.append(self._persist_signal(signal))
                except Exception as e:
                    logger.error(f"Strategy error {strat.strategy_id}: {e}")

        # If we have async tasks (persistence), schedule them
        # Since this method is sync, we can't await. 
        # But actually _process_jsonl_line is called from async loop usually.
        # Refactor: _on_new_1m_bar should be async or return awaitables.
        pass # Dealing with async in next step (run loop) which will call this.
        # Actually, let's make this method async or return tasks?
        # The caller acts as the driver.

    async def on_new_1m_bar_async(self, symbol: str):
        bars = list(self.bars_1m[symbol])
        
        for tf in self.config.timeframes:
            resampled = resample_bars(bars, tf)
            if not resampled: continue
            
            last_bar = resampled[-1]
            last_ts = last_bar.ts
            if self.processed_state[symbol].get(tf) == last_ts:
                continue
            
            self.processed_state[symbol][tf] = last_ts
            
            for strat in self.strategies:
                if tf in strat.required_timeframes:
                    try:
                        signal = strat.on_bars(symbol, tf, resampled)
                        if signal:
                            # Dedup
                            sig_key = f"{signal.ts}_{signal.symbol}_{signal.timeframe}_{signal.strategy_id}_{signal.direction}"
                            if sig_key not in self._emitted_signals:
                                logger.info(f"Signal Generated: {signal}")
                                await self._persist_signal(signal)
                                self._emitted_signals.add(sig_key)
                                
                                if len(self._emitted_signals) > 2000:
                                    self._emitted_signals.clear()
                    except Exception as e:
                        logger.error(f"Strategy error {strat.strategy_id}: {e}")

    async def run_tail_jsonl(self, duration: int = 0):
        # Tail the latest/today specific file? 
        # For simplicity, let's assume we tail all recent kline_1m files in input_dir
        # But "tail -f" style on multiple files is complex in python.
        # Simplified approach for smoke: 
        # 1. Identify active kline_1m files for today.
        # 2. Poll them for new lines.
        
        await self._init_storage()
        self.running = True
        end_time = time.time() + duration if duration > 0 else float('inf')
        
        # Find files
        # data/realtime/YYYY-MM-DD/kline_SYMBOL_1m.jsonl
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = Path(self.config.input_root) / today
        
        cursors = {} # filepath -> file_handle, position
        
        while self.running:
            if duration > 0 and time.time() >= end_time:
                break
                
            # Scan for new files or ensure open
            # We want kline_*.jsonl
            if day_dir.exists():
                for f in day_dir.glob("kline_*_1m.jsonl"):
                    if str(f) not in cursors:
                        fh = open(f, "r")
                        # If we want to process HISTORY, read from start.
                        # If we want only NEW, seek to end.
                        # Requirement: "buffer... via last price... or just use kline_1m".
                        # To build meaningful buffer (MA needs 20 periods), we probably need history.
                        # So read from start.
                        cursors[str(f)] = fh
            
            data_found = False
            for fpath, fh in cursors.items():
                line = fh.readline()
                while line:
                    self._process_jsonl_line(line)
                    # Helper to parse symbol from line or filename is done in _process...
                    # We need to trigger async processing.
                    # Ideally we extract symbol inside _process... and return it.
                    # Quick hack: parse symbol from fpath?
                    # fpath: .../kline_BTCUSDT_1m.jsonl
                    parts = Path(fpath).stem.split('_') # kline, BTCUSDT, 1m
                    if len(parts) >= 2:
                        symbol = parts[1]
                        await self.on_new_1m_bar_async(symbol)
                    
                    data_found = True
                    line = fh.readline()
            
            if not data_found:
                await asyncio.sleep(0.1)
                
        # Close handles
        for fh in cursors.values():
            fh.close()
        
        if self.signal_file:
            await self.signal_file.close()

    async def run(self, duration: int = 0):
        if self.config.mode == "tail_jsonl":
            await self.run_tail_jsonl(duration)
        else:
            logger.warning("Unsupported mode")
