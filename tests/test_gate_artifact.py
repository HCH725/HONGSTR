import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

class TestGateArtifact(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.run_dir = self.test_dir / "test_run"
        self.run_dir.mkdir()

        # Create a mock regime_report.json
        self.regime_data = {
            "buckets": {
                "BULL": {
                    "sharpe": 0.4,
                    "max_drawdown": -0.10,
                    "trades_count": 120
                },
                "BEAR": {
                    "sharpe": 0.05,
                    "max_drawdown": -0.35,
                    "trades_count": 50
                },
                "NEUTRAL": {
                    "sharpe": 0.25,
                    "max_drawdown": -0.05,
                    "trades_count": 150
                }
            }
        }
        with open(self.run_dir / "regime_report.json", "w") as f:
            json.dump(self.regime_data, f)

        # Create a mock summary.json (Schema 2 Requirement)
        self.summary_data = {
            "start_ts": "2024-01-01T00:00:00Z",
            "end_ts": "2024-01-31T23:59:59Z",
            "trades_count": 50, # 31 days * 0.5 = 15.5 < 30 (default min) -> FAIL
            "exposure_time": 0.5,
            "per_symbol": {
                "BTCUSDT_4h": {"trades_count": 30},
                "ETHUSDT_4h": {"trades_count": 20}
            }
        }
        with open(self.run_dir / "summary.json", "w") as f:
            json.dump(self.summary_data, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_gate_generation_full_pass_fail(self):
        # Run script for FULL mode
        # BULL: 0.4 > 0.3 (OK), -0.1 > -0.25 (OK)
        # BEAR: 0.05 < 0.1 (FAIL), -0.35 < -0.3 (FAIL)
        # NEUTRAL: 0.25 > 0.2 (OK), -0.05 > -0.25 (OK)
        # Portfolio: 50 trades > 30 required (OK)

        cmd = [
            "python3", "scripts/generate_gate_artifact.py",
            "--dir", str(self.run_dir),
            "--mode", "FULL",
            "--symbols", "BTCUSDT,ETHUSDT",
            "--timeframe", "4h"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        gate_path = self.run_dir / "gate.json"
        self.assertTrue(gate_path.exists())

        with open(gate_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["schema_version"], 2)
        self.assertFalse(data["results"]["overall"]["pass"])

        # Check reasons
        reasons = data["results"]["overall"]["reasons"]
        self.assertTrue(any("BEAR: sharpe 0.05 < 0.10" in r for r in reasons))
        self.assertTrue(any("BEAR: max_mdd -0.35 < -0.30" in r for r in reasons))

    def test_gate_generation_short_pass(self):
        # Run script for SHORT mode
        # Thresholds for SHORT are all 0/0.15.
        # BULL: 0.4 > 0 (OK), -0.1 > -0.15 (OK)
        # BEAR: 0.05 > 0 (OK), -0.35 < -0.15 (FAIL) -> FAIL
        # Adjusting BEAR MDD to pass

        self.regime_data["buckets"]["BEAR"]["max_drawdown"] = -0.05
        with open(self.run_dir / "regime_report.json", "w") as f:
            json.dump(self.regime_data, f)

        cmd = [
            "python3", "scripts/generate_gate_artifact.py",
            "--dir", str(self.run_dir),
            "--mode", "SHORT",
            "--symbols", "BTCUSDT",
            "--timeframe", "4h"
        ]
        subprocess.run(cmd, check=True)

        with open(self.run_dir / "gate.json", "r") as f:
            data = json.load(f)
        self.assertTrue(data["results"]["overall"]["pass"])
        self.assertEqual(len(data["results"]["overall"]["reasons"]), 0)

if __name__ == "__main__":
    unittest.main()
