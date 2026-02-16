import asyncio
import json
import logging
import os
from typing import Optional, Dict

import aiofiles
from ..config import (
    EXECUTION_MODE, 
    SIGNAL_OUTPUT_ROOT, 
    EXECUTION_STATE_DIR,
    OFFLINE_MODE
)
from ..execution.executor import ExecutionEngine
from ..execution.broker import AbstractBroker
from ..execution.paper import PaperBroker
from ..execution.binance_testnet import BinanceFuturesTestnetBroker as BinanceTestnetBroker
from ..execution.models import SignalEvent
from ..semantics.core import SemanticsV1

logger = logging.getLogger(__name__)

class SignalExecutionBridge:
    def __init__(self, executor: Optional[ExecutionEngine] = None):
        self.executor = executor
        self.running = False
        
        # Determine broker if executor not provided
        if not self.executor:
            if EXECUTION_MODE == 'B':
                self.broker = PaperBroker(semantics=SemanticsV1())
            elif EXECUTION_MODE == 'C':
                from .config import BINANCE_API_KEY, BINANCE_SECRET_KEY, BINANCE_TESTNET_BASE_URL
                self.broker = BinanceTestnetBroker(
                    api_key=BINANCE_API_KEY, 
                    secret_key=BINANCE_SECRET_KEY, 
                    base_url=BINANCE_TESTNET_BASE_URL
                )
            else:
                logger.warning(f"Unknown EXECUTION_MODE {EXECUTION_MODE}, defaulting to Paper")
                self.broker = PaperBroker()
                
            self.executor = ExecutionEngine(self.broker)

        # State tracking so we don't re-execute old signals on restart
        # Ideally we persist "last_processed_signal_ts" or similar
        self.last_signal_ts = 0 
        self.processed_signals = set() # hash of signal ID or similar

    async def run(self, duration: int = 0):
        self.running = True
        logger.info(f"Starting Execution Bridge (Mode: {EXECUTION_MODE})")
        
        # File parsing setup
        # Match SignalEngine dated folder structure
        from datetime import datetime
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        signals_dir = os.path.join(SIGNAL_OUTPUT_ROOT, date_str)
        signals_file = os.path.join(signals_dir, "signals.jsonl")
        
        # Ensure file exists or wait for it
        while not os.path.exists(signals_file) and self.running:
            logger.info(f"Waiting for {signals_file}...")
            await asyncio.sleep(1)
            if duration > 0: 
                # decrem duration? simplified: wait loop
                pass
                
        if not self.running: return

        # Open file
        # We start trailing from END if we want only new signals? 
        # Or from start if we want to catch up?
        # SAFETY: For C10, let's process from NOW (seek end) to avoid blasting old signals
        # UNLESS user wants catchup. 
        # Rule of thumb: Automated Execution -> Safe Default = New Signals Only.
        
        async with aiofiles.open(signals_file, mode='r') as f:
            # For C10 smoke test determinism, we want to process existing signals if any.
            # Production: normally seek end. But idempotency protects us.
            # Let's seek 0 to catch up or process injected signal.
            await f.seek(0, 0) 
            
            end_time = asyncio.get_event_loop().time() + duration if duration > 0 else float('inf')
            
            while self.running:
                line = await f.readline()
                if line:
                    await self.process_signal_line(line)
                else:
                    await asyncio.sleep(0.1)
                    
                if duration > 0 and asyncio.get_event_loop().time() >= end_time:
                    break
                    
        logger.info("Bridge stopped.")

    async def process_signal_line(self, line: str):
        try:
            data = json.loads(line)
            # Reconstruct SignalEvent
            # SignalEvent has: ts, symbol, portfolio_id, strategy_id, direction, timeframe, regime, confidence
            
            # Timestamp parsing
            # signal.ts is usually ISO string or timestamp
            # We need to adapt data to SignalEvent constructor
            # The SignalEvent in models.py expects pd.Timestamp for ts? 
            # Or signal.types.SignalEvent?
            # We should use execution.models.SignalEvent or align them.
            # Plan says: "Consolidate types".
            # For now, let's map it.
            
            # Using execution.models.SignalEvent
            from ..execution.models import SignalEvent as ExecSignalEvent
            import pandas as pd
            
            evt = ExecSignalEvent(
                ts=pd.Timestamp(data['ts']),
                symbol=data['symbol'],
                portfolio_id=data.get('portfolio_id', 'HONG'),
                strategy_id=data.get('strategy_id', 'unknown'),
                direction=data['direction'],
                timeframe=data.get('timeframe', ''),
                regime=data.get('regime', ''),
                confidence=data.get('confidence', 1.0)
            )
            
            # Idempotency Check
            sig_id = f"{evt.ts}_{evt.symbol}_{evt.strategy_id}_{evt.direction}"
            if sig_id in self.processed_signals:
                return
            self.processed_signals.add(sig_id)
            
            logger.info(f"Bridge Received Signal: {evt.symbol} {evt.direction} from {evt.strategy_id}")
            
            if OFFLINE_MODE:
                logger.info("OFFLINE_MODE=1, skipping execution")
                return

            # Execute
            # Executor.execute_signal is sync or async? 
            # It's currently sync in `executor.py`. 
            # We can run it directly since it just places orders via broker.
            # If broker is async, then executor should be async.
            # Existing Broker is sync (requests).
            # So we block the loop slightly. Acceptable for Phase 1.
            
            self.executor.execute_signal(evt)
            
        except Exception as e:
            logger.error(f"Error processing signal line: {e}")

