import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestWalkforwardLatestUpdatePolicy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.reports = self.tmp / "reports"
        self.reports.mkdir(parents=True)
        self.config = self.tmp / "windows.json"
        self.run_dir = self.tmp / "run_dir"
        self.run_dir.mkdir(parents=True)
        self.windows = [
            {"name": "W1_BULL", "start": "2021-01-01", "end": "2021-06-01"},
            {"name": "W2_BEAR", "start": "2022-01-01", "end": "2022-06-01"},
        ]
        self.config.write_text(json.dumps(self.windows), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _run_report(
        self, run_id: str, rows: list[str], suite_mode: str = "FULL_SUITE"
    ) -> subprocess.CompletedProcess:
        out = self.reports / "walkforward" / run_id
        out.mkdir(parents=True, exist_ok=True)
        suite = out / "suite_results.tsv"
        suite.write_text("\n".join(rows) + "\n", encoding="utf-8")
        return subprocess.run(
            [
                "python3",
                "scripts/report_walkforward.py",
                "--config",
                str(self.config),
                "--reports_dir",
                str(self.reports),
                "--run_id",
                run_id,
                "--suite_results_tsv",
                str(suite),
                "--suite_mode",
                suite_mode,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_failed_run_does_not_overwrite_latest(self):
        stale = {
            "run_id": "old_ok",
            "status": "COMPLETED",
            "windows_total": 2,
            "windows_completed": 2,
            "windows_failed": 0,
            "windows": [],
            "latest_updated": True,
            "latest_update_reason": "all windows completed",
        }
        (self.reports / "walkforward_latest.json").write_text(
            json.dumps(stale), encoding="utf-8"
        )
        ok_row = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"  # noqa: E501
        fail_row = "W2_BEAR\t2022-01-01\t2022-06-01\tFAILED\t-\tUNKNOWN\tUNKNOWN\tpipeline_exit_1\tBTCUSDT"  # noqa: E501

        cp = self._run_report("run_fail", [ok_row, fail_row])
        self.assertEqual(cp.returncode, 0)
        self.assertIn("WARN reason=LATEST_NOT_UPDATED_FAILED", cp.stdout)

        latest = json.loads(
            (self.reports / "walkforward_latest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(latest["run_id"], "old_ok")

    def test_success_run_updates_latest_and_gate_message_contract(self):
        row1 = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"  # noqa: E501
        row2 = f"W2_BEAR\t2022-01-01\t2022-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tHOLD\t-\tBTCUSDT"  # noqa: E501

        cp = self._run_report("run_ok", [row1, row2])
        self.assertEqual(cp.returncode, 0)
        self.assertIn("LATEST_UPDATED run_id=run_ok", cp.stdout)
        self.assertIn("latest_json=", cp.stdout)

        latest = json.loads(
            (self.reports / "walkforward_latest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(latest["run_id"], "run_ok")
        self.assertTrue(latest["latest_updated"])
        self.assertIn(
            "latest updated ->", Path("scripts/gate_all.sh").read_text(encoding="utf-8")
        )

    def test_quick_mode_success_updates_latest(self):
        stale = {
            "run_id": "old_ok",
            "status": "COMPLETED",
            "windows_total": 2,
            "windows_completed": 2,
            "windows_failed": 0,
            "windows": [],
            "latest_updated": True,
            "latest_update_reason": "all windows completed",
        }
        (self.reports / "walkforward_latest.json").write_text(
            json.dumps(stale), encoding="utf-8"
        )
        row1 = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"  # noqa: E501
        row2 = f"W2_BEAR\t2022-01-01\t2022-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tHOLD\t-\tBTCUSDT"  # noqa: E501
        cp = self._run_report("run_quick_ok", [row1, row2], suite_mode="QUICK")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("LATEST_UPDATED run_id=run_quick_ok", cp.stdout)
        latest = json.loads(
            (self.reports / "walkforward_latest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(latest["run_id"], "run_quick_ok")
        self.assertTrue(latest["latest_updated"])
        self.assertEqual(
            latest.get("latest_pointer_policy"), "allow_update_quick_completed"
        )

    def test_quick_mode_partial_selection_updates_latest(self):
        self.windows.append(
            {"name": "W3_SIDEWAYS", "start": "2023-01-01", "end": "2023-06-01"}
        )
        self.config.write_text(json.dumps(self.windows), encoding="utf-8")

        stale = {
            "run_id": "old_ok",
            "status": "COMPLETED",
            "windows_total": 3,
            "windows_completed": 3,
            "windows_failed": 0,
            "windows": [],
            "latest_updated": True,
            "latest_update_reason": "all windows completed",
        }
        (self.reports / "walkforward_latest.json").write_text(
            json.dumps(stale), encoding="utf-8"
        )

        row1 = f"W1_BULL\t2021-01-01\t2021-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tTRADE\t-\tBTCUSDT"  # noqa: E501
        row2 = f"W2_BEAR\t2022-01-01\t2022-06-01\tCOMPLETED\t{self.run_dir}\tPASS\tHOLD\t-\tBTCUSDT"  # noqa: E501
        cp = self._run_report("run_quick_partial_ok", [row1, row2], suite_mode="QUICK")
        self.assertEqual(cp.returncode, 0)
        self.assertIn("LATEST_UPDATED run_id=run_quick_partial_ok", cp.stdout)
        self.assertNotIn("LATEST_NOT_UPDATED_QUICK_MODE", cp.stdout)

        latest = json.loads(
            (self.reports / "walkforward_latest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(latest["run_id"], "run_quick_partial_ok")
        self.assertTrue(latest["latest_updated"])
        self.assertEqual(
            latest.get("latest_pointer_policy"), "allow_update_quick_completed"
        )
        self.assertEqual(latest["windows_total"], 3)
        self.assertEqual(latest["windows_selected"], 2)
        self.assertEqual(latest["windows_completed"], 2)


if __name__ == "__main__":
    unittest.main()
