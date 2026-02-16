import asyncio
import logging
import sys
import argparse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from hongstr.config import (
    REALTIME_SYMBOLS,
    SIGNAL_TFS,
    SIGNAL_INPUT_ROOT,
    SIGNAL_OUTPUT_ROOT,
    SIGNAL_STATE_ROOT,
    SIGNAL_ENGINE_MODE,
    SIGNAL_MAX_BARS
)
from hongstr.signal.engine import SignalEngine
from hongstr.signal.types import EngineConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_signal")

async def main():
    parser = argparse.ArgumentParser(description="Run Signal Engine")
    parser.add_argument("--symbols", type=str, default=",".join(REALTIME_SYMBOLS))
    parser.add_argument("--tfs", type=str, default=",".join(SIGNAL_TFS))
    parser.add_argument("--mode", type=str, default=SIGNAL_ENGINE_MODE)
    parser.add_argument("--duration", type=int, default=60)
    
    args = parser.parse_args()
    
    symbols = args.symbols.split(",")
    tfs = args.tfs.split(",")
    
    logger.info("--- Starting Signal Engine ---")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Timeframes: {tfs}")
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Duration: {args.duration}s")
    
    config = EngineConfig(
        symbols=symbols,
        timeframes=tfs,
        input_root=SIGNAL_INPUT_ROOT,
        output_root=SIGNAL_OUTPUT_ROOT,
        state_root=SIGNAL_STATE_ROOT,
        mode=args.mode,
        max_bars=SIGNAL_MAX_BARS
    )
    
    engine = SignalEngine(config)
    
    try:
        await engine.run(duration=args.duration)
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
        
    logger.info("--- Signal Engine Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
