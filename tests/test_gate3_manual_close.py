from hongstr.execution.models import OrderRequest
from hongstr.execution.paper import PaperBroker
from hongstr.reconcile.reconciler import Reconciler
from hongstr.semantics.core import SemanticsV1


def test_gate3_manual_close_orphan_cancellation(tmp_path):
    sem = SemanticsV1()
    broker = PaperBroker(sem)
    broker.paper_dir = tmp_path

    # 1. Setup: Orphan Orders (Bracket leftovers)
    # Position = NONE (Manual close simulated by clearing position)
    # Open Orders = STOP, TAKE_PROFIT

    broker.open_orders = []
    broker.positions = {} # No Valid Position

    # Add dummy orders directly to internal list for PaperBroker simulation
    # Or use place_order with LIMIT which queues them.

    # Place STOP (SL)
    sl_req = OrderRequest("BTCUSDT", "SELL", 1.0, "STOP", price=45000.0, reduce_only=True)
    broker.place_order(sl_req)

    # Place TP
    tp_req = OrderRequest("BTCUSDT", "SELL", 1.0, "TAKE_PROFIT", price=55000.0, reduce_only=True)
    broker.place_order(tp_req)

    assert len(broker.get_open_orders("BTCUSDT")) == 2

    # 2. Run Reconciler
    reconciler = Reconciler(broker)
    reconciler.run_once()

    # 3. Assertions
    # Orders should be cancelled because position matches 'NONE'
    assert len(broker.get_open_orders("BTCUSDT")) == 0
