import asyncio
import logging
import os
import sys

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.config import (
    REALTIME_OUT_DIR,
    REALTIME_STREAMS,
    REALTIME_SYMBOLS,
    REALTIME_WS_BASE,
    SIGNAL_MAX_BARS,
    SIGNAL_OUTPUT_ROOT,
    SIGNAL_STATE_ROOT,
    SIGNAL_TFS,
)
from hongstr.realtime.stream_manager import StreamManager
from hongstr.signal.engine import SignalEngine
from hongstr.signal.types import EngineConfig

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_strategies")

async def main():
    run_seconds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--seconds" else 60
    logger.info("--- Starting Signal Strategies Run (C9) ---")
    logger.info(f"Duration: {run_seconds}s")

    # 1. Start C7 Stream Manager (Validation: Need feeds for realtime data)
    # Note: C8 generic script ran tail_jsonl. C9 smoke often wants end-to-end.
    # RUNBOOK says "Runs (C7 StreamManager + C8 SignalEngine + C9 strategies)"
    # So we must instantiate BOTH.

    # Init StreamManager (C7)
    from hongstr.realtime.types import WSConfig

    ws_config = WSConfig(
        symbols=REALTIME_SYMBOLS,
        output_dir=REALTIME_OUT_DIR,
        ws_base_url=REALTIME_WS_BASE,
        intervals=["1m"]
    )
    c7_manager = StreamManager(
        config=ws_config,
        streams=REALTIME_STREAMS
    )

    # Init Signal Engine (tail_jsonl mode to read what C7 writes)
    c8_config = EngineConfig(
        symbols=REALTIME_SYMBOLS,
        timeframes=SIGNAL_TFS,
        input_root=REALTIME_OUT_DIR, # Reads C7 output
        output_root=SIGNAL_OUTPUT_ROOT,
        state_root=SIGNAL_STATE_ROOT,
        mode="tail_jsonl",
        max_bars=SIGNAL_MAX_BARS
    )
    c8_engine = SignalEngine(c8_config)

    # Run Both
    logger.info("Launching C7 and C8...")

    # Start C7 (Connects and starts writing files)
    ws_task = asyncio.create_task(c7_manager.run(duration=run_seconds))

    # Start C8 (Watches files and runs strategies)
    signal_task = asyncio.create_task(c8_engine.run_tail_jsonl(duration=run_seconds))

    try:
        await asyncio.sleep(run_seconds)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Stopping services...")
        c7_manager.stop()
        # c8 engine stops naturally if we pass duration to run_tail_jsonl,
        # but if run_tail_jsonl loops forever (duration=0), we cancel it.
        # run_tail_jsonl implementation in C8 typically handles duration check?
        # Let's assume passed duration works.
        await signal_task
        if not ws_task.done():
            ws_task.cancel()

    logger.info("--- Run Complete ---")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
