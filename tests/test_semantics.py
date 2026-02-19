from hongstr.semantics.core import SemanticsV1


def test_semantics_fees():
    sem = SemanticsV1(taker_fee_rate=0.0005)
    notional = 1000.0
    fee = sem.calc_fee(notional)
    assert fee == 0.5


def test_semantics_slippage():
    sem = SemanticsV1(slippage_bps=10.0)  # 0.1%
    price = 100.0

    # Buy slippage adds to price
    buy_price = sem.apply_slippage(price, "BUY")
    assert buy_price == 100.0 + (100.0 * 0.001)  # 100.1

    # Sell slippage subtracts
    sell_price = sem.apply_slippage(price, "SELL")
    assert sell_price == 100.0 - (100.0 * 0.001)  # 99.9


def test_semantics_funding():
    sem = SemanticsV1()
    # Long pays positive rate
    fee = sem.calc_funding(position_notional=10000, funding_rate=0.0001)
    # 10000 * 0.0001 = 1.0.
    # Paying means PnL impact is negative.
    assert fee == -1.0

    # Short receives positive rate
    # Position = -10000
    fee = sem.calc_funding(position_notional=-10000, funding_rate=0.0001)
    # -1 * -10000 * 0.0001 = 1.0
    # Receiving means PnL impact is positive.
    assert fee == 1.0
