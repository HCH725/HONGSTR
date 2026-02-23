import pandas as pd
import pytest
from research.panel.gates import gate_unique_key, gate_sorted, gate_coverage

def test_gate_unique_key_pass():
    df = pd.DataFrame({"close": [1, 2, 3]}, index=pd.MultiIndex.from_tuples([
        (pd.Timestamp("2020-01-01"), "BTCusdt"),
        (pd.Timestamp("2020-01-02"), "BTCusdt"),
        (pd.Timestamp("2020-01-01"), "ETHusdt"),
    ]))
    assert gate_unique_key(df) is True

def test_gate_unique_key_fail():
    df = pd.DataFrame({"close": [1, 2]}, index=pd.MultiIndex.from_tuples([
        (pd.Timestamp("2020-01-01"), "BTCusdt"),
        (pd.Timestamp("2020-01-01"), "BTCusdt"), # duplicated
    ]))
    assert gate_unique_key(df) is False

def test_gate_sorted_pass():
    df = pd.DataFrame({"close": [1, 2]}, index=pd.MultiIndex.from_tuples([
        (pd.Timestamp("2020-01-01"), "BTCusdt"),
        (pd.Timestamp("2020-01-02"), "BTCusdt"),
    ]))
    assert gate_sorted(df) is True

def test_gate_sorted_fail():
    df = pd.DataFrame({"close": [1, 2]}, index=pd.MultiIndex.from_tuples([
        (pd.Timestamp("2020-01-02"), "BTCusdt"),
        (pd.Timestamp("2020-01-01"), "BTCusdt"),
    ]))
    assert gate_sorted(df) is False

def test_gate_coverage_pass():
    df = pd.DataFrame({
        "open": [1, 2],
        "high": [1, 2],
        "low": [1, 2],
        "close": [1, 2],
        "volume": [10, 20]
    })
    assert gate_coverage(df) is True

def test_gate_coverage_missing_cols_fail():
    df = pd.DataFrame({"close": [1, 2]})
    assert gate_coverage(df) is False

def test_gate_coverage_high_gap_fail():
    # 5 rows, 3 nulls = 60% missing, which is > 5% allowed
    df = pd.DataFrame({
        "open": [1, None, None, None, 2],
        "high": [1, None, None, None, 2],
        "low": [1, None, None, None, 2],
        "close": [1, None, None, None, 2],
        "volume": [1, None, None, None, 2],
    })
    assert gate_coverage(df) is False
