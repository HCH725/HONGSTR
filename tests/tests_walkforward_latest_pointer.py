import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestWalkforwardLatestPointer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.reports = self.tmp / "reports"
        self.run_dir = self.tmp / "run"
        self.config = self.tmp / "windows.json"
        self.reports.mkdir(parents=True)
        self.run_dir.mkdir(parents=True)

        self.windows = [
            {"name": "W1_BULL", "start": "2021-01-01", "end": "2021-06-01"},
            {"name": "W2_BEAR", "start": "2022-01-01", "end": "2022-06-01"},
        ]
        self.config.write_text(json.dumps(self.windows), encoding="utf-8")

        stale = {
            "run_id": "stale_ok",
            "status": "COMPLETED",
            "windows_total": 5,
            "windows_completed": 5,
            "windows_failed": 0,
            "windows": [],
            "latest_updated": True,
            "latest_update_reason": "all windows completed",
        }
        (self.reports / "walkforward_latest.json").write_text(
            json.dumps(stale), encoding="utf-8"
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_latest_pointer_not_overwritten_when_failed(self):
        out = self.reports / "walkforward" / "new_run"
        out.mkdir(parents=True, exist_ok=True)
        suite = out / "suite_results.tsv"
        suite.write_text(
            "\n".join(
                [
                    f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT",
                    "W2_BEAR\t2022-01-01\t2022-06-01\tFAILED\t-\tUNKNOWN\tUNKNOWN\tpipeline_exit_1\tBTCUSDT",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        cp = subprocess.run(
            [
                "python3",
                "scripts/report_walkforward.py",
                "--config",
                str(self.config),
                "--reports_dir",
                str(self.reports),
                "--run_id",
                "new_run",
                "--suite_results_tsv",
                str(suite),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0)
        self.assertIn("LATEST_NOT_UPDATED_STALE_RISK", cp.stdout)
        self.assertIn("failed_windows=W2_BEAR", cp.stdout)

        latest = json.loads(
            (self.reports / "walkforward_latest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(latest["run_id"], "stale_ok")

        run_report = json.loads(
            (self.reports / "walkforward" / "new_run" / "walkforward.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(run_report["latest_updated"])
        self.assertEqual(
            run_report["latest_warning_reason"], "LATEST_NOT_UPDATED_STALE_RISK"
        )


if __name__ == "__main__":
    unittest.main()
