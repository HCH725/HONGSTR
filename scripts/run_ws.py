import asyncio
import logging
import sys
from pathlib import Path

# Add src to path so we can import hongstr
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root / "src"))

from hongstr.config import (
    REALTIME_OUT_DIR,
    REALTIME_RUN_SECONDS,
    REALTIME_STREAMS,
    REALTIME_SYMBOLS,
    REALTIME_WS_BASE,
)
from hongstr.realtime.stream_manager import StreamManager
from hongstr.realtime.types import WSConfig

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("run_ws")

async def main():
    logger.info("--- Starting Realtime WS Smoke Test ---")
    logger.info(f"Symbols: {REALTIME_SYMBOLS}")
    logger.info(f"Streams: {REALTIME_STREAMS}")
    logger.info(f"Output Dir: {REALTIME_OUT_DIR}")
    logger.info(f"Duration: {REALTIME_RUN_SECONDS}s")

    config = WSConfig(
        symbols=REALTIME_SYMBOLS,
        intervals=[], # intervals are embedded in streams list for this simple manager
        output_dir=REALTIME_OUT_DIR,
        ws_base_url=REALTIME_WS_BASE,
        run_seconds=REALTIME_RUN_SECONDS
    )

    manager = StreamManager(config, REALTIME_STREAMS)

    try:
        await manager.run(duration=REALTIME_RUN_SECONDS)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

    logger.info(f"Total messages processed: {manager.msg_count}")

    # List created files
    logger.info("Files created:")
    out_path = Path(REALTIME_OUT_DIR)
    if out_path.exists():
        for f in out_path.glob("**/*.jsonl"):
            logger.info(f" - {f} ({f.stat().st_size} bytes)")

    logger.info("--- Smoke Test Complete ---")

if __name__ == "__main__":
    asyncio.run(main())
