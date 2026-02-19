import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

import argparse

from hongstr.config import EXECUTION_MODE, RECONCILE_INTERVAL_SEC
from hongstr.execution.binance_testnet import BinanceFuturesTestnetBroker
from hongstr.execution.paper import PaperBroker
from hongstr.reconcile.reconciler import Reconciler
from hongstr.semantics.core import SemanticsV1


def run_loop():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()

    print(f"--- Reconcile Loop (Mode: {EXECUTION_MODE}) ---")

    if EXECUTION_MODE == "C":
        broker = BinanceFuturesTestnetBroker()
    else:
        broker = PaperBroker(SemanticsV1())

    reconciler = Reconciler(broker)

    try:
        while True:
            print(f"[{pd.Timestamp.now()}] Reconciling...")
            reconciler.run_once()
            if args.once:
                break
            time.sleep(RECONCILE_INTERVAL_SEC)
    except KeyboardInterrupt:
        print("Stopping.")


import pandas as pd  # Delayed import fix above  # noqa: E402

if __name__ == "__main__":
    run_loop()
