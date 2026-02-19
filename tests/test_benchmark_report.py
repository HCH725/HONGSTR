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


class TestBenchmarkReport(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.reports_dir = self.test_dir / "reports"
        self.reports_dir.mkdir()

        # Create a mock benchmark_latest.json
        self.bench_data = {
            "schema_version": 1,
            "generated_at": "2023-10-27T10:00:00Z",
            "FULL": {
                "run_dir": "/path/to/full",
                "top": {
                    "total_return": 0.15,
                    "max_drawdown": -0.05,
                    "sharpe": 1.2,
                    "trades_count": 500,
                },
                "per_symbol_4h": {
                    "BTCUSDT_4h": {
                        "total_return": 0.1,
                        "max_drawdown": -0.04,
                        "sharpe": 0.8,
                        "trades_count": 200,
                        "win_rate": 0.55,
                    }
                },
                "gate_overall": {"pass": True, "reasons": []},
            },
            "SHORT": {
                "run_dir": "/path/to/short",
                "top": {
                    "total_return": 0.05,
                    "max_drawdown": -0.02,
                    "sharpe": 0.9,
                    "trades_count": 100,
                },
                "per_symbol_4h": {
                    "BTCUSDT_4h": {
                        "total_return": 0.04,
                        "max_drawdown": -0.01,
                        "sharpe": 0.7,
                        "trades_count": 40,
                        "win_rate": 0.6,
                    }
                },
                "gate_overall": {"pass": False, "reasons": ["SHORT: MDD failed"]},
            },
        }
        self.bench_path = self.reports_dir / "benchmark_latest.json"
        with open(self.bench_path, "w") as f:
            json.dump(self.bench_data, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_report_cli_table(self):
        cmd = ["python3", "scripts/report_benchmark.py", "--path", str(self.bench_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)

        output = result.stdout
        self.assertIn("BTCUSDT_4h", output)
        self.assertIn("15.00%", output)  # FULL return
        self.assertIn("1.200", output)  # FULL sharpe
        self.assertIn("GATE: PASS", output)
        self.assertIn("GATE: FAIL", output)
        self.assertIn("SHORT: MDD failed", output)


if __name__ == "__main__":
    unittest.main()
