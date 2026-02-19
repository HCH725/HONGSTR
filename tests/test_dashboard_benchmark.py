import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Mock streamlit before import
sys.modules["streamlit"] = MagicMock()


# Configure mocks to avoid errors during import
# Use side_effect to handle different column counts (3 for Environment, 3 for Selection, 2 for Benchmark, 2 for Opt)
def mock_columns(n):
    return [MagicMock() for _ in range(n)]


sys.modules["streamlit"].columns.side_effect = mock_columns
sys.modules["streamlit"].sidebar.selectbox.return_value = "No Runs Found"

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

import scripts.dashboard as dashboard


class TestDashboardBenchmark(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_root = dashboard.PROJECT_ROOT
        dashboard.PROJECT_ROOT = Path(self.test_dir)

        # Create reports dir
        self.reports_dir = Path(self.test_dir) / "reports"
        self.reports_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        dashboard.PROJECT_ROOT = self.original_root

    def test_load_benchmark_missing(self):
        # Should return None if file missing
        data = dashboard.load_benchmark_data()
        self.assertIsNone(data)

    def test_load_benchmark_valid(self):
        # Create valid json
        data = {
            "generated_at": "2023-01-01T00:00:00Z",
            "FULL": {
                "top": {"total_return": 0.1, "sharpe": 1.5},
                "per_symbol_4h": {"BTCUSDT_4h": {"total_return": 0.05}},
            },
            "SHORT": {"top": {"total_return": 0.01}, "per_symbol_4h": {}},
        }
        (self.reports_dir / "benchmark_latest.json").write_text(json.dumps(data))

        loaded = dashboard.load_benchmark_data()
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["FULL"]["top"]["total_return"], 0.1)

    def test_safe_get(self):
        d = {"a": {"b": 1}}
        self.assertEqual(dashboard.safe_get(d, "a", "b"), 1)
        self.assertEqual(dashboard.safe_get(d, "a", "c", default=99), 99)
        self.assertIsNone(dashboard.safe_get(d, "x"))


if __name__ == "__main__":
    unittest.main()
