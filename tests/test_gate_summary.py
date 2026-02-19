import unittest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

# Import the script module (a bit hacky, but works for script testing)
from scripts import gate_summary

class TestGateSummary(unittest.TestCase):
    def setUp(self):
        self.result = gate_summary.GateResult()

    def test_check_metrics_pass(self):
        # Good metrics
        metrics = {
            "trades_count": 50,
            "max_drawdown": -0.10,
            "exposure_time": 0.50,
            "sharpe": 1.5,
            "total_return": 0.10
        }
        gate_summary.check_metrics("TestPass", metrics, self.result)
        self.assertEqual(len(self.result.errors), 0)

    def test_check_metrics_fail_trades(self):
        # Too few trades
        metrics = {
            "trades_count": 10, # < 30
            "max_drawdown": -0.10,
            "exposure_time": 0.50,
            "sharpe": 1.5
        }
        gate_summary.check_metrics("TestFailTrades", metrics, self.result)
        self.assertTrue(any("Trades" in e for e in self.result.errors))

    def test_check_metrics_fail_mdd(self):
        # MDD too deep (<= -0.25)
        metrics = {
            "trades_count": 50,
            "max_drawdown": -0.30, # <= -0.25 check
            "exposure_time": 0.50,
            "sharpe": 1.5
        }
        gate_summary.check_metrics("TestFailMDD", metrics, self.result)
        self.assertTrue(any("MaxDD" in e for e in self.result.errors))

    def test_check_metrics_fail_sharpe(self):
        # Sharpe too low (< -0.2)
        metrics = {
            "trades_count": 50,
            "max_drawdown": -0.10,
            "exposure_time": 0.50,
            "sharpe": -0.5
        }
        gate_summary.check_metrics("TestFailSharpe", metrics, self.result)
        self.assertTrue(any("Sharpe" in e for e in self.result.errors))

    def test_integration_logic(self):
        # Simulate a full summary json structure
        data = {
            "per_symbol": {
                "BTCUSDT_1h": {
                    "trades_count": 50,
                    "max_drawdown": -0.05,
                    "exposure_time": 0.6,
                    "sharpe": 1.0,
                    "total_return": 0.1
                },
                "BTCUSDT_4h": {
                    "trades_count": 40,
                    "max_drawdown": -0.1,
                    "exposure_time": 0.8,
                    "sharpe": 0.5,
                    "total_return": 0.05
                }
            }
        }
        
        # Manually invoke logic similar to main (mocking isn't easy for script main)
        # We just verify check_metrics works on these.
        for k, v in data["per_symbol"].items():
            gate_summary.check_metrics(k, v, self.result)
            
        self.assertEqual(len(self.result.errors), 0)

if __name__ == "__main__":
    unittest.main()
