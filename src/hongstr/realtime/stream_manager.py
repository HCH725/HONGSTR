import asyncio
import json
import logging
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Any

import aiofiles
import websockets
from websockets.exceptions import ConnectionClosed

from .binance_ws import build_stream_url
from .types import WSConfig

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self, config: WSConfig, streams: List[str]):
        self.config = config
        self.streams = streams  # e.g. ["aggTrade", "kline_1m"]
        self.running = False
        self.ws = None
        self.connect_attempts = 0
        self.msg_count = 0
        self.files_cache: Dict[Tuple[str, str, str], Any] = {}
        
        # Ensure output directory exists
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

    async def _get_file_handle(self, symbol: str, stream_type: str, date_str: str):
        key = (symbol, stream_type, date_str)
        if key in self.files_cache:
            return self.files_cache[key]
            
        day_dir = Path(self.config.output_dir) / date_str
        if not day_dir.exists():
            day_dir.mkdir(parents=True, exist_ok=True)
            
        if stream_type == "aggTrade":
             filename = f"aggTrade_{symbol}.jsonl"
        elif stream_type.startswith("kline_"):
             # kline_1m -> kline_BTCUSDT_1m.jsonl
             interval = stream_type.split("_")[1]
             filename = f"kline_{symbol}_{interval}.jsonl"
        else:
             filename = f"{stream_type}_{symbol}.jsonl"
             
        filepath = day_dir / filename
        self.files_cache[key] = await aiofiles.open(filepath, mode='a', encoding='utf-8')
        return self.files_cache[key]

    async def _write_message(self, message: dict):
        try:
            stream_name = message.get("stream")
            data = message.get("data")
            if not stream_name or not data:
                return

            parts = stream_name.split('@')
            if len(parts) != 2:
                return
            
            symbol = parts[0].upper()
            stream_type = parts[1]

            ts_local = datetime.now().isoformat()
            record = {
                "ts_local": ts_local,
                "stream": stream_name,
                "data": data
            }
            
            date_str = datetime.now().strftime("%Y-%m-%d")
            fh = await self._get_file_handle(symbol, stream_type, date_str)
            await fh.write(json.dumps(record) + "\n")
            await fh.flush()
            
            self.msg_count += 1
            
        except Exception as e:
            logger.error(f"Error writing message: {e}")

    async def _close_files(self):
        for fh in self.files_cache.values():
            await fh.close()
        self.files_cache.clear()

    def stop(self):
        logger.info("Stopping StreamManager...")
        self.running = False

    async def run(self, duration: int = 0):
        self.running = True
        url = build_stream_url(self.config.ws_base_url, self.config.symbols, self.streams)
        
        # Install signal handlers if we are in the main thread/loop
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, self.stop)
        except NotImplementedError:
            # Not supported in this environment (e.g. some thread loops)
            pass

        end_time = time.time() + duration if duration > 0 else float('inf')
        
        logger.info(f"Connecting to {url}")
        
        while self.running:
            if duration > 0 and time.time() >= end_time:
                break
                
            try:
                async with websockets.connect(url) as ws:
                    self.ws = ws
                    self.connect_attempts = 0
                    logger.info("WebSocket connected")
                    
                    while self.running:
                        if duration > 0 and time.time() >= end_time:
                            break
                        
                        try:
                            # Use short timeout to allow checking self.running and duration
                            msg_raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                            msg = json.loads(msg_raw)
                            await self._write_message(msg)
                        except asyncio.TimeoutError:
                            continue
                        except ConnectionClosed:
                            logger.warning("Connection closed")
                            break
                        except Exception as e:
                            logger.error(f"Error processing: {e}")
                            
            except Exception as e:
                logger.error(f"Connection failed/dropped: {e}")
                if self.running:
                    # Exponential backoff
                    wait_time = min(60, 2**self.connect_attempts)
                    logger.info(f"Reconnecting in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self.connect_attempts += 1
        
        await self._close_files()
        logger.info("StreamManager shutdown complete")
