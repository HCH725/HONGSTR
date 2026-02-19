import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Path Hack to find src
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from hongstr.config import REALTIME_SYMBOLS, SIGNAL_OUTPUT_ROOT


def inject_signal():
    # 1. Determine Target File
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_dir = Path(SIGNAL_OUTPUT_ROOT) / today
    signals_dir.mkdir(parents=True, exist_ok=True)
    signals_file = signals_dir / "signals.jsonl"

    # 2. Schema Construction
    # Based on src/hongstr/signal/types.py SignalEvent
    # @dataclass
    # class SignalEvent:
    #     ts: pd.Timestamp
    #     symbol: str
    #     portfolio_id: str
    #     strategy_id: str
    #     direction: str  # 'LONG', 'SHORT', 'FLAT'
    #     timeframe: str
    #     regime: str = "NEUTRAL"
    #     confidence: float = 1.0
    #     reason: str = ""
    #     source: str = "realtime"

    symbol = REALTIME_SYMBOLS[0] if REALTIME_SYMBOLS else "BTCUSDT"
    now_iso = datetime.now(timezone.utc).isoformat()

    # Mock Signal
    signal_data = {
        "ts": now_iso,
        "symbol": symbol,
        "portfolio_id": "HONG",
        "strategy_id": "smoke_test_injector",
        "direction": "LONG",
        "timeframe": "1m",
        "regime": "TREND",
        "confidence": 1.0,
        "reason": "Deterministic Smoke Test Injection",
        "source": "manual_injection",
    }

    # 3. Write to File
    print(f"Injecting signal to {signals_file}:")
    print(json.dumps(signal_data, indent=2))

    with open(signals_file, "a") as f:
        f.write(json.dumps(signal_data) + "\n")

    print("Injection Complete.")


if __name__ == "__main__":
    inject_signal()
