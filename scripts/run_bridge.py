import argparse
import asyncio
import logging
import os
import sys

# Path Hack
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.bridge.signal_to_execution import SignalExecutionBridge
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
from hongstr.realtime.types import WSConfig
from hongstr.signal.engine import SignalEngine
from hongstr.signal.types import EngineConfig

# Setup Logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("run_bridge")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seconds", type=int, default=30, help="Run duration in seconds"
    )
    parser.add_argument(
        "--mode", type=str, default="B", help="Execution Mode (B=Paper)"
    )
    args = parser.parse_args()

    run_seconds = args.seconds

    logger.info("--- Starting Bridge Run (C10) ---")
    logger.info(f"Duration: {run_seconds}s, Mode: {args.mode}")

    # 1. Stream Manager (C7)
    ws_config = WSConfig(
        symbols=REALTIME_SYMBOLS,
        output_dir=REALTIME_OUT_DIR,
        ws_base_url=REALTIME_WS_BASE,
        intervals=["1m"],
    )
    c7_manager = StreamManager(config=ws_config, streams=REALTIME_STREAMS)

    # 2. Signal Engine (C8)
    c8_config = EngineConfig(
        symbols=REALTIME_SYMBOLS,
        timeframes=SIGNAL_TFS,
        input_root=REALTIME_OUT_DIR,
        output_root=SIGNAL_OUTPUT_ROOT,
        state_root=SIGNAL_STATE_ROOT,
        mode="tail_jsonl",
        max_bars=SIGNAL_MAX_BARS,
    )
    c8_engine = SignalEngine(c8_config)

    # Ensure signals file exists for bridge to tail
    from datetime import datetime

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    signals_dir = os.path.join(SIGNAL_OUTPUT_ROOT, date_str)
    signals_file = os.path.join(signals_dir, "signals.jsonl")

    if not os.path.exists(signals_dir):
        os.makedirs(signals_dir, exist_ok=True)
    if not os.path.exists(signals_file):
        with open(signals_file, "w"):
            pass

    # 3. Execution Bridge (C10)
    # Ensure mode env var is set if needed by internal logic,
    # though we pass it via config imports usually.
    # Code reads os.getenv("EXECUTION_MODE"), so let's override if arg provided
    if args.mode:
        os.environ["EXECUTION_MODE"] = args.mode

    bridge = SignalExecutionBridge()

    # Launch All
    logger.info("Launching C7, C8, and Bridge...")

    tasks = [
        asyncio.create_task(c7_manager.run(duration=run_seconds)),
        asyncio.create_task(c8_engine.run_tail_jsonl(duration=run_seconds)),
        asyncio.create_task(bridge.run(duration=run_seconds)),
    ]

    try:
        await asyncio.gather(*tasks)
    except Exception as e:
        logger.error(f"Run Error: {e}")
    finally:
        logger.info("Stopping...")
        c7_manager.stop()

    logger.info("--- Bridge Run Complete ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
