import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRerunFailedWindows(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.report = self.tmp / "walkforward.json"
        self.config = self.tmp / "windows.json"
        self.config.write_text(
            json.dumps(
                [
                    {"name": "BULL_2021_H1", "start": "2021-01-01", "end": "2021-05-31"},
                    {"name": "BEAR_2022", "start": "2022-01-01", "end": "2022-12-31"},
                ]
            ),
            encoding="utf-8",
        )
        payload = {
            "run_id": "wf_failed_001",
            "windows": [
                {
                    "name": "BULL_2021_H1",
                    "start": "2021-01-01",
                    "end": "2021-05-31",
                    "status": "FAILED",
                    "symbols": ["BTCUSDT"],
                },
                {
                    "name": "BEAR_2022",
                    "start": "2022-01-01",
                    "end": "2022-12-31",
                    "status": "ERROR",
                    "symbols": ["BTCUSDT", "ETHUSDT"],
                },
            ],
            "failed_windows_summary": [
                {"name": "BULL_2021_H1", "status": "FAILED", "error": "pipeline_exit_1"},
                {"name": "BEAR_2022", "status": "ERROR", "error": "missing_out_dir"},
            ],
        }
        self.report.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_dry_run_emits_failed_windows_and_command_count(self):
        cp = subprocess.run(
            [
                "bash",
                "scripts/rerun_failed_windows.sh",
                "--report_json",
                str(self.report),
                "--config",
                str(self.config),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertIn("FAILED_COUNT\t2", cp.stdout)
        self.assertIn("WINDOW\tBULL_2021_H1\t2021-01-01\t2021-05-31\tBTCUSDT", cp.stdout)
        self.assertIn("WINDOW\tBEAR_2022\t2022-01-01\t2022-12-31\tBTCUSDT,ETHUSDT", cp.stdout)
        self.assertEqual(cp.stdout.count("[DRY-RUN] bash scripts/run_and_verify.sh"), 2)
        self.assertIn("commands=2", cp.stdout)


if __name__ == "__main__":
    unittest.main()
