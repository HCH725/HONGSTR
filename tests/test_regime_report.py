import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

# Add project root
sys_path = Path(__file__).parent.parent
import sys

sys.path.append(str(sys_path))

import scripts.generate_regime_report as reporter


class TestRegimeReport(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.data_root = self.test_dir / "data"
        self.run_dir = self.test_dir / "run_01"

        # Setup Dirs
        (self.data_root / "derived" / "BTCUSDT" / "4h").mkdir(parents=True)
        self.run_dir.mkdir(parents=True)

        # 1. Mock Summary
        (self.run_dir / "summary.json").write_text(json.dumps({
            "start_ts": "2023-01-01", "end_ts": "2023-01-10"
        }))

        # 2. Mock BTC 4h (Regime Input)
        # Create timestamps cover 10 days
        dates = pd.date_range("2023-01-01", periods=60, freq="4h", tz="UTC")
        prices = np.linspace(100, 200, 60) # Uptrend -> Bull
        df_btc = pd.DataFrame({
            "ts": dates, "open": prices, "high": prices+1, "low": prices-1, "close": prices, "volume": 100
        })
        df_btc.to_json(self.data_root / "derived" / "BTCUSDT" / "4h" / "klines.jsonl", orient="records", lines=True, date_format="iso")

        # 3. Mock Equity Curve
        # Corresponds to dates
        df_eq = pd.DataFrame({
            "ts": dates,
            "equity": np.linspace(1000, 1100, 60)
        })
        df_eq.to_json(self.run_dir / "equity_curve.jsonl", orient="records", lines=True, date_format="iso")

        # 4. Mock Trades
        df_trades = pd.DataFrame({
            "ts_entry": [dates[10], dates[20]],
            "ts_exit": [dates[12], dates[22]],
            "symbol": ["BTCUSDT", "ETHUSDT"],
            "pnl": [10, 20],
            "pnl_pct": [0.01, 0.02]
        })
        df_trades.to_json(self.run_dir / "trades.jsonl", orient="records", lines=True, date_format="iso")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_report(self):
        # We need to mock RegimeLabeler because it might not be importable or we want controlled output
        # But for integration, let's try to run it if available, or mock it if not.

        # Mocking RegimeLabeler to return BULL for all
        with patch("scripts.generate_regime_report.RegimeLabeler") as MockLabeler:
            instance = MockLabeler.return_value
            # return dataframe with BULL
            dates = pd.date_range("2023-01-01", periods=60, freq="4h", tz="UTC")
            df_labels = pd.DataFrame({"regime": ["BULL"]*60}, index=dates)
            instance.label_regime.return_value = df_labels.squeeze() # return Series

            reporter.generate_report(self.run_dir, self.data_root)

            report_path = self.run_dir / "regime_report.json"
            self.assertTrue(report_path.exists())

            data = json.loads(report_path.read_text())
            self.assertEqual(data["timeframe_regime"], "4h")
            self.assertEqual(data["regime_series_source"], "computed")

            # Check Buckets
            bull = data["buckets"]["BULL"]
            self.assertGreater(bull["total_return"], 0)
            self.assertEqual(bull["trades_count"], 2) # Both trades in BULL

            # Check Per Symbol
            self.assertIn("BTCUSDT", bull["per_symbol"])
            self.assertEqual(bull["per_symbol"]["BTCUSDT"]["trades_count"], 1)

if __name__ == "__main__":
    unittest.main()
