import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestWalkForwardReport(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.reports_dir = self.test_dir / "reports"
        self.config_path = self.test_dir / "windows.json"
        self.run_dir = self.test_dir / "run_a"
        self.reports_dir.mkdir(parents=True)
        self.run_dir.mkdir(parents=True)

        self.windows = [
            {"name": "W1_BULL", "start": "2021-01-01", "end": "2021-06-01"},
            {"name": "W2_BEAR", "start": "2022-01-01", "end": "2022-06-01"},
        ]
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(self.windows, handle)

        with open(self.run_dir / "summary.json", "w", encoding="utf-8") as handle:
            json.dump(
                {"sharpe": 2.0, "max_drawdown": -0.1, "total_return": 0.5}, handle
            )
        with open(self.run_dir / "gate.json", "w", encoding="utf-8") as handle:
            json.dump({"results": {"overall": {"pass": True}}}, handle)
        with open(self.run_dir / "selection.json", "w", encoding="utf-8") as handle:
            json.dump({"decision": "TRADE"}, handle)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _run_report(self, run_id: str, rows: list[str]) -> subprocess.CompletedProcess:
        run_out = self.reports_dir / "walkforward" / run_id
        run_out.mkdir(parents=True, exist_ok=True)
        suite_tsv = run_out / "suite_results.tsv"
        with open(suite_tsv, "w", encoding="utf-8") as handle:
            handle.write("\n".join(rows) + "\n")

        cmd = [
            "python3",
            "scripts/report_walkforward.py",
            "--config",
            str(self.config_path),
            "--reports_dir",
            str(self.reports_dir),
            "--run_id",
            run_id,
            "--suite_results_tsv",
            str(suite_tsv),
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_failed_run_does_not_update_latest(self):
        ok_row = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"
        fail_row = (
            "W2_BEAR\t2022-01-01\t2022-06-01\tFAILED\t"
            "-\tUNKNOWN\tUNKNOWN\tINSUFFICIENT_DATA_RESAMPLE;exit=1;log=foo.log;out_dir=bar\tBTCUSDT"
        )
        result = self._run_report("run_fail", [ok_row, fail_row])
        self.assertEqual(result.returncode, 0)

        run_json = self.reports_dir / "walkforward" / "run_fail" / "walkforward.json"
        self.assertTrue(run_json.exists())
        payload = json.load(open(run_json, "r", encoding="utf-8"))
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["windows_completed"], 1)
        self.assertEqual(payload["windows_total"], 2)
        self.assertEqual(payload["failed_windows_summary"][0]["name"], "W2_BEAR")
        self.assertIn(
            "INSUFFICIENT_DATA_RESAMPLE", payload["failed_windows_summary"][0]["error"]
        )
        self.assertFalse(payload["latest_updated"])
        self.assertFalse((self.reports_dir / "walkforward_latest.json").exists())

    def test_complete_run_updates_latest(self):
        row1 = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"
        row2 = f"W2_BEAR\t2022-01-01\t2022-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tHOLD\t-\tBTCUSDT"
        result = self._run_report("run_ok", [row1, row2])
        self.assertEqual(result.returncode, 0)

        latest_json = self.reports_dir / "walkforward_latest.json"
        self.assertTrue(latest_json.exists())
        latest = json.load(open(latest_json, "r", encoding="utf-8"))
        self.assertEqual(latest["status"], "COMPLETED")
        self.assertEqual(latest["windows_completed"], 2)
        self.assertTrue(latest["latest_updated"])


if __name__ == "__main__":
    unittest.main()
