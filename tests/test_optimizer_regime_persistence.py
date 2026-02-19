import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from hongstr.selection.selection import get_best_params_for_regime  # noqa: E402


class TestOptimizerRegimePersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.run_dir = self.test_dir / "test_run"
        self.run_dir.mkdir()

        # 1. Mock summary.json
        self.summary_data = {
            "run_id": "test_run_123",
            "total_return": 0.1,
            "sharpe": 1.5,
            "max_drawdown": -0.05,
            "config": {"symbols": ["BTCUSDT"], "timeframes": ["4h"]},
        }
        with open(self.run_dir / "summary.json", "w") as f:
            json.dump(self.summary_data, f)

        # 2. Mock regime_report.json
        self.regime_data = {
            "buckets": {
                "BULL": {
                    "count_periods": 100,
                    "sharpe": 2.0,
                    "total_return": 0.05,
                    "max_drawdown": -0.01,
                    "trades_count": 50,
                },
                "BEAR": {
                    "count_periods": 50,
                    "sharpe": 0.5,
                    "total_return": -0.02,
                    "max_drawdown": -0.05,
                    "trades_count": 10,
                },
                "NEUTRAL": {
                    "count_periods": 200,
                    "sharpe": 1.0,
                    "total_return": 0.02,
                    "max_drawdown": -0.02,
                    "trades_count": 25,
                },
            }
        }
        with open(self.run_dir / "regime_report.json", "w") as f:
            json.dump(self.regime_data, f)

        # 3. Mock optimizer.json
        self.opt_data = {"best": {"params": {"atr_period": 14, "atr_mult": 2.5}}}
        with open(self.run_dir / "optimizer.json", "w") as f:
            json.dump(self.opt_data, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_artifact_generation(self):
        import subprocess

        cmd = [
            "python3",
            "scripts/generate_optimizer_regime_artifact.py",
            "--run_dir",
            str(self.run_dir),
            "--regime_tf",
            "4h",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        reg_opt_path = self.run_dir / "optimizer_regime.json"
        self.assertTrue(reg_opt_path.exists())

        with open(reg_opt_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 1)
        self.assertIn("BULL", data["buckets"])
        self.assertEqual(len(data["buckets"]["BULL"]["topk"]), 1)
        self.assertEqual(data["buckets"]["BULL"]["topk"][0]["params"]["atr_period"], 14)
        self.assertIn(
            "Insufficient samples: trades 10 < 30", data["buckets"]["BEAR"]["warnings"]
        )

    def test_selection_api(self):
        # Generate artifact first
        import subprocess

        subprocess.run(
            [
                "python3",
                "scripts/generate_optimizer_regime_artifact.py",
                "--run_dir",
                str(self.run_dir),
            ],
            check=True,
        )

        # Test API
        best_bull = get_best_params_for_regime(str(self.run_dir), "BULL")
        self.assertIsNotNone(best_bull)
        self.assertEqual(best_bull["atr_period"], 14)

        # Test Fallback (remove optimizer_regime.json)
        os.remove(self.run_dir / "optimizer_regime.json")
        best_fallback = get_best_params_for_regime(str(self.run_dir), "BEAR")
        self.assertEqual(
            best_fallback["atr_period"], 14
        )  # Should come from optimizer.json

        # Test None fallback
        os.remove(self.run_dir / "optimizer.json")
        self.assertIsNone(get_best_params_for_regime(str(self.run_dir), "NEUTRAL"))


if __name__ == "__main__":
    unittest.main()
