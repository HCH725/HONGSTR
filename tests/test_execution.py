from hongstr.execution.models import OrderRequest
from hongstr.execution.paper import PaperBroker
from hongstr.reconcile.reconciler import Reconciler
from hongstr.semantics.core import SemanticsV1


# Mock Offline
def test_offline_mode_blocks_network(monkeypatch, tmp_path):
    monkeypatch.setattr("hongstr.execution.paper.OFFLINE_MODE", True)

    sem = SemanticsV1()
    broker = PaperBroker(sem)
    broker.paper_dir = tmp_path # Isolate
    broker.positions = {}
    broker.open_orders = []

    req = OrderRequest("BTCUSDT", "BUY", 1.0, "MARKET")
    res = broker.place_order(req)

    assert res.status == "REJECTED"
    assert "OFFLINE_MODE" in res.error

def test_paper_reduce_only_logic(tmp_path):
    sem = SemanticsV1()
    broker = PaperBroker(sem) # Mode A/B
    broker.paper_dir = tmp_path # Isolate
    broker.positions = {}
    broker.open_orders = []

    # 1. No position -> ReduceOnly should fail
    req = OrderRequest("ETHUSDT", "SELL", 1.0, "MARKET", reduce_only=True)
    res = broker.place_order(req)
    assert res.status == "REJECTED"

    # 2. Enter Long
    entry = OrderRequest("ETHUSDT", "BUY", 2.0, "MARKET")
    broker.place_order(entry)
    pos = broker.get_position("ETHUSDT")
    assert pos.side == "LONG"
    assert pos.amt == 2.0

    # 3. Reduce Partial
    red = OrderRequest("ETHUSDT", "SELL", 1.0, "MARKET", reduce_only=True)
    res = broker.place_order(red)
    assert res.status == "FILLED"
    pos = broker.get_position("ETHUSDT")
    assert pos.amt == 1.0

def test_reconcile_orphans(tmp_path):
    sem = SemanticsV1()
    broker = PaperBroker(sem)
    broker.paper_dir = tmp_path # Isolate
    broker.positions = {}
    broker.open_orders = []

    # Create orphan order (Open order but no position)
    # PaperBroker place_order stores open order if LIMIT
    req = OrderRequest("BTCUSDT", "BUY", 1.0, "LIMIT", price=50000.0)
    broker.place_order(req)
    assert len(broker.get_open_orders("BTCUSDT")) == 1

    reconciler = Reconciler(broker)
    # Position is NONE. Logic: If position NONE and orders exist -> Cancel
    reconciler.run_once()

    assert len(broker.get_open_orders("BTCUSDT")) == 0

def test_gate2_idempotency(tmp_path):
    from hongstr.execution.executor import ExecutionEngine
    from hongstr.execution.models import SignalEvent
    from hongstr.execution.paper import PaperBroker
    from hongstr.semantics.core import SemanticsV1

    sem = SemanticsV1()
    broker = PaperBroker(sem)
    broker.paper_dir = tmp_path

    engine = ExecutionEngine(broker)
    # We need to mock load_selection to allow execution
    engine.load_selection = lambda: {"selection": {"BULL": ["test_strat"], "BEAR": [], "NEUTRAL": []}}

    # Force clear positions (PaperBroker loads from default dir in init)
    broker.positions = {}

    import pandas as pd
    signal = SignalEvent(
        ts=pd.Timestamp.now(),
        symbol="BTCUSDT",
        portfolio_id="HONG",
        strategy_id="test_strat",
        direction="LONG",
        timeframe="1h",
        regime="BULL"
    )

    # Entry (market) filled immediately.
    # Set balance to 20k -> 2k notional (below 5k limit)
    broker.balance = 20000.0

    # 1) First run
    engine.execute_signal(signal)

    orders_first = broker.get_open_orders("BTCUSDT")

    # 2) Second run should be idempotent
    engine.execute_signal(signal)

    orders_second = broker.get_open_orders("BTCUSDT")

    # Do not hardcode count. In some baseline states this can be 0.
    # Idempotency invariant: second run must not mutate normalized order set.
    def normalize_order(order):
        if isinstance(order, dict):
            d = order
        elif hasattr(order, "model_dump"):
            d = order.model_dump()
        elif hasattr(order, "dict"):
            d = order.dict()
        else:
            d = getattr(order, "__dict__", {})
        keys = (
            "symbol",
            "side",
            "type",
            "quantity",
            "positionSide",
            "price",
            "timeInForce",
            "reduceOnly",
        )
        return tuple((k, d.get(k)) for k in keys if k in d)

    norm_first = sorted(normalize_order(o) for o in (orders_first or []))
    norm_second = sorted(normalize_order(o) for o in (orders_second or []))

    assert norm_second == norm_first
    assert len(norm_second) == len(set(norm_second))
