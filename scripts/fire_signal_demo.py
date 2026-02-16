import sys
import pandas as pd
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from hongstr.execution.models import SignalEvent
from hongstr.execution.paper import PaperBroker
from hongstr.execution.executor import ExecutionEngine
from hongstr.semantics.core import SemanticsV1
from hongstr.config import EXECUTION_MODE

def fire_signal():
    print(f"--- Firing Demo Signal (Mode: {EXECUTION_MODE}) ---")
    
    # Setup
    sem = SemanticsV1()
    broker = PaperBroker(sem) # Force Paper for demo usually
    # If Mode C, use Testnet? 
    # For fail safety, script defaults to Paper unless env set?
    # Uses imports, so respects config.
    
    if EXECUTION_MODE == 'C':
        from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
        broker = BinanceFuturesTestnetBroker()
    
    engine = ExecutionEngine(broker)
    
    # Signal
    sig = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="Manual_Demo",
        direction="LONG",
        timeframe="1h",
        regime="BULL"
    )
    
    print(f"Signal: {sig}")
    engine.execute_signal(sig)
    print("Executed. Check logs/state.")

if __name__ == "__main__":
    fire_signal()
