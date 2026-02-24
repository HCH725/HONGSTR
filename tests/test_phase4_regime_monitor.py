import pytest
import json
import numpy as np
from scripts.phase4_regime_monitor import compute_thresholds, evaluate

def test_compute_thresholds():
    # Mock Phase 3 data with 5 walks
    mock_data = {
        "walks": [
            {"sharpe": 1.0, "mdd": -0.05, "trades": 100},
            {"sharpe": 1.5, "mdd": -0.04, "trades": 120},
            {"sharpe": 0.5, "mdd": -0.06, "trades": 80},
            {"sharpe": 2.0, "mdd": -0.03, "trades": 150},
            {"sharpe": 0.0, "mdd": -0.07, "trades": 50},
        ]
    }
    
    thresholds = compute_thresholds(mock_data)
    
    # Sharpe: median of [0, 0.5, 1.0, 1.5, 2.0] is 1.0
    # IQR: 75th (1.5) - 25th (0.5) = 1.0
    assert thresholds["sharpe"]["median"] == 1.0
    assert thresholds["sharpe"]["iqr"] == 1.0
    assert thresholds["sharpe"]["warn"] == 0.5 # 1.0 - 0.5 * 1.0
    assert thresholds["sharpe"]["fail"] == 0.0 # 1.0 - 1.0 * 1.0
    
    # Trades: median of [50, 80, 100, 120, 150] is 100
    assert thresholds["trades"]["median"] == 100
    assert thresholds["trades"]["warn_gate"] == 50
    
    # MDD: p80 (20th percentile) and p95 (5th percentile)
    # mdds sorted: [-0.07, -0.06, -0.05, -0.04, -0.03]
    # np.percentile([-0.07, -0.06, -0.05, -0.04, -0.03], 20) -> -0.062
    assert thresholds["mdd"]["p80"] < -0.05
    assert thresholds["mdd"]["p95"] < thresholds["mdd"]["p80"]

def test_evaluate_ok():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": 1.2, "trades_count": 100, "max_drawdown": -0.04}
    status, reasons = evaluate(current, thresholds)
    assert status == "OK"
    assert "All metrics within Phase 3 comfort zone" in reasons[0]

def test_evaluate_warn_sharpe():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": 0.3, "trades_count": 100, "max_drawdown": -0.04}
    status, reasons = evaluate(current, thresholds)
    assert status == "WARN"
    assert "Sharpe (0.300)" in reasons[0]

def test_evaluate_warn_trades():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": 1.2, "trades_count": 40, "max_drawdown": -0.04}
    status, reasons = evaluate(current, thresholds)
    assert status == "WARN"
    assert "Trade Count (40)" in reasons[0]

def test_evaluate_warn_mdd():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": 1.2, "trades_count": 100, "max_drawdown": -0.07}
    status, reasons = evaluate(current, thresholds)
    assert status == "WARN"
    assert "MDD (-7.00%)" in reasons[0]

def test_evaluate_fail_sharpe():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": -0.1, "trades_count": 100, "max_drawdown": -0.04}
    status, reasons = evaluate(current, thresholds)
    assert status == "FAIL"
    assert "Sharpe (-0.100)" in reasons[0]

def test_evaluate_fail_mdd():
    thresholds = {
        "sharpe": {"warn": 0.5, "fail": 0.0},
        "trades": {"warn_gate": 50},
        "mdd": {"p80": -0.06, "p95": -0.08}
    }
    current = {"sharpe": 1.2, "trades_count": 100, "max_drawdown": -0.09}
    status, reasons = evaluate(current, thresholds)
    assert status == "FAIL"
    assert "MDD (-9.00%)" in reasons[0]
