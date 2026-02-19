import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from hongstr.selection.selection import get_current_selection, load_selection


class TestSelectionPersistence(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.run_dir = self.test_dir / "test_run_sel"
        self.run_dir.mkdir()

        # 1. Mock inputs
        # Regime Report (BULL)
        with open(self.run_dir / "regime_report.json", "w") as f:
            json.dump({"latest_regime": "BULL", "buckets": {}}, f)

        # Gate (PASS)
        with open(self.run_dir / "gate.json", "w") as f:
            json.dump({"results": {"overall": {"pass": True, "reasons": []}}}, f)

        # Optimizer Regime
        # Provide candidate for BULL
        with open(self.run_dir / "optimizer_regime.json", "w") as f:
            json.dump(
                {
                    "buckets": {
                        "BULL": {
                            "topk": [
                                {
                                    "params": {"atr_period": 10},
                                    "score": {"sharpe": 2.0},
                                    "metrics": {"sharpe": 2.0},
                                }
                            ]
                        }
                    }
                },
                f,
            )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def run_generator(self, respect_gate="true"):
        import subprocess

        cmd = [
            "python3",
            "scripts/generate_selection_artifact.py",
            "--run_dir",
            str(self.run_dir),
            "--respect_gate",
            respect_gate,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_trade_decision(self):
        # Case 1: Pass Gate -> TRADE
        self.run_generator(respect_gate="true")

        sel = load_selection(str(self.run_dir))
        self.assertEqual(sel["decision"], "TRADE")
        self.assertEqual(sel["regime"], "BULL")
        self.assertEqual(sel["selected"]["params"]["atr_period"], 10)

        # API Check
        api_res = get_current_selection(str(self.run_dir))
        self.assertEqual(api_res["decision"], "TRADE")
        self.assertEqual(api_res["source"], "selection_artifact")

    def test_hold_decision(self):
        # Case 2: Fail Gate -> HOLD
        # Update gate to fail
        with open(self.run_dir / "gate.json", "w") as f:
            json.dump(
                {
                    "results": {
                        "overall": {"pass": False, "reasons": ["Sharpe too low"]}
                    }
                },
                f,
            )

        self.run_generator(respect_gate="true")

        sel = load_selection(str(self.run_dir))
        self.assertEqual(sel["decision"], "HOLD")
        self.assertIn("Gate FAIL", sel["reasons"][0])

        # Check selected is present but decision is HOLD
        # (Implementation detail: we populate 'selected' for observation even on hold?
        # Script logic: if can_trade is False, selected is None/skipped implementation-wise unless enforced.
        # My script implementation set selected=None if !can_trade.
        self.assertIsNone(sel["selected"])

    def test_force_trade_ignore_gate(self):
        # Case 3: Fail Gate but respect_gate=false -> TRADE
        with open(self.run_dir / "gate.json", "w") as f:
            json.dump(
                {
                    "results": {
                        "overall": {"pass": False, "reasons": ["Sharpe too low"]}
                    }
                },
                f,
            )

        self.run_generator(respect_gate="false")

        sel = load_selection(str(self.run_dir))
        self.assertEqual(sel["decision"], "TRADE")
        self.assertIsNotNone(sel["selected"])


if __name__ == "__main__":
    unittest.main()
