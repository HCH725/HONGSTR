import unittest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import subprocess

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))

class TestOptimizerPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.run_dir = Path(self.test_dir) / "run_123"
        self.run_dir.mkdir(parents=True)
        
        # Create dummy summary.json
        self.summary = {
            "run_id": "run_123",
            "timestamp": "2023-01-01T00:00:00Z",
            "total_return": 0.1,
            "sharpe": 1.5,
            "max_drawdown": -0.05,
            "config": {
                "symbols": ["BTCUSDT"],
                "timeframes": ["4h"]
            },
            "per_symbol": {}
        }
        with open(self.run_dir / "summary.json", 'w') as f:
            json.dump(self.summary, f)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_generate_optimizer_artifact(self):
        # Run script via subprocess to test end-to-end logic
        script_path = Path(__file__).parent.parent / "scripts" / "generate_optimizer_artifact.py"
        
        result = subprocess.run(
            [sys.executable, str(script_path), "--dir", str(self.run_dir)],
            capture_output=True,
            text=True
        )
        
        self.assertEqual(result.returncode, 0, f"Script failed: {result.stderr}")
        
        # Check artifact
        opt_path = self.run_dir / "optimizer.json"
        self.assertTrue(opt_path.exists())
        
        with open(opt_path, 'r') as f:
            data = json.load(f)
            
        self.assertEqual(data["run_id"], "run_123")
        self.assertEqual(data["best"]["metrics_portfolio"]["total_return"], 0.1)
        self.assertEqual(data["schema_version"], "1.0")

if __name__ == "__main__":
    unittest.main()
