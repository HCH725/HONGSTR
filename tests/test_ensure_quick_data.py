import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestEnsureQuickData(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.config = self.tmp / "windows.json"
        self.config.write_text(
            json.dumps(
                [
                    {"name": "W1", "start": "2026-02-14", "end": "2026-02-15"},
                    {"name": "W2", "start": "2026-02-16", "end": "2026-02-17"},
                ]
            ),
            encoding="utf-8",
        )
        self.data_root = self.tmp / "data" / "derived"
        self.report = self.tmp / "reports" / "quick_data_check.md"

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_generates_seed_data_and_report(self):
        cp = subprocess.run(
            [
                "bash",
                "scripts/ensure_quick_data.sh",
                "--symbols",
                "BTCUSDT",
                "--config",
                str(self.config),
                "--quick_windows",
                "2",
                "--data_root",
                str(self.data_root),
                "--report",
                str(self.report),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertTrue(self.report.exists())
        content = self.report.read_text(encoding="utf-8")
        self.assertIn("Quick Data Check", content)
        self.assertIn("BTCUSDT", content)

        data_file = self.data_root / "BTCUSDT" / "1m" / "klines.jsonl"
        self.assertTrue(data_file.exists())
        lines = [x for x in data_file.read_text(encoding="utf-8").splitlines() if x.strip()]
        self.assertGreater(len(lines), 1000)


if __name__ == "__main__":
    unittest.main()
