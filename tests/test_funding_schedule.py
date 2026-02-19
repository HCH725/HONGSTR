import pandas as pd

from hongstr.semantics.core import SemanticsV1


def test_funding_schedule_utc():
    sem = SemanticsV1()

    # Case 1: UTC timestamps
    ts_funding = pd.Timestamp("2024-01-01 08:00:00").tz_localize("UTC")
    assert sem.is_funding_timestamp(ts_funding) is True

    ts_no_funding = pd.Timestamp("2024-01-01 09:00:00").tz_localize("UTC")
    assert sem.is_funding_timestamp(ts_no_funding) is False

    # Case 2: Asia/Taipei timestamps (GMT+8)
    # 08:00 UTC = 16:00 Taipei. Should be True.
    ts_taipei_funding = pd.Timestamp("2024-01-01 16:00:00").tz_localize("Asia/Taipei")
    assert sem.is_funding_timestamp(ts_taipei_funding) is True

    # 00:00 UTC = 08:00 Taipei. Should be True.
    ts_taipei_funding_2 = pd.Timestamp("2024-01-01 08:00:00").tz_localize("Asia/Taipei")
    assert sem.is_funding_timestamp(ts_taipei_funding_2) is True

    # 00:00 Taipei = 16:00 (prev day) UTC. Should be True.
    ts_taipei_funding_3 = pd.Timestamp("2024-01-02 00:00:00").tz_localize("Asia/Taipei")
    assert sem.is_funding_timestamp(ts_taipei_funding_3) is True

    # Random time
    ts_taipei_random = pd.Timestamp("2024-01-01 12:00:00").tz_localize(
        "Asia/Taipei"
    )  # 04:00 UTC
    assert sem.is_funding_timestamp(ts_taipei_random) is False


def test_funding_schedule_naive():
    # If naive, assumes UTC
    sem = SemanticsV1()
    ts_naive = pd.Timestamp("2024-01-01 08:00:00")
    assert sem.is_funding_timestamp(ts_naive) is True
