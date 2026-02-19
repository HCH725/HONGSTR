import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRerunLatestPointer(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.runner = self.tmp / "fake_runner.sh"
        self.runner.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    'OUT_DIR="$(mktemp -d /tmp/hongstr_fake_run_XXXX)"',
                    'echo \'{"results":{"overall":{"pass":true}}}\' > "$OUT_DIR/gate.json"',  # noqa: E501
                    'echo \'{"decision":"HOLD"}\' > "$OUT_DIR/selection.json"',
                    'echo "OUT_DIR: $OUT_DIR"',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.runner.chmod(0o755)
        self.reports = self.tmp / "reports"
        self.walkforward = self.reports / "walkforward"
        self.walkforward.mkdir(parents=True, exist_ok=True)

        self.latest_json = self.reports / "walkforward_latest.json"
        self.latest_md = self.reports / "walkforward_latest.md"
        self.rerun_json = self.reports / "walkforward_rerun_latest.json"
        self.rerun_md = self.reports / "walkforward_rerun_latest.md"

        sentinel = {"run_id": "sentinel_full_suite", "latest_updated": True}
        self.latest_json.write_text(json.dumps(sentinel), encoding="utf-8")
        self.latest_md.write_text("# sentinel\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _build_source_report(
        self, run_id: str, windows: list[dict], failed_names: list[str]
    ) -> Path:
        run_dir = self.walkforward / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": run_id,
            "windows": windows,
            "failed_windows_summary": [
                {"name": n, "status": "FAILED", "error": "x"} for n in failed_names
            ],
        }
        report = run_dir / "walkforward.json"
        report.write_text(json.dumps(payload), encoding="utf-8")
        return report

    def _run_rerun(
        self, report_json: Path, config_path: Path
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                "bash",
                "scripts/rerun_failed_windows.sh",
                "--report_json",
                str(report_json),
                "--config",
                str(config_path),
                "--runner_script",
                str(self.runner),
                "--reports_dir",
                str(self.reports),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_partial_rerun_updates_rerun_latest_only(self):
        windows = [
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
                "status": "FAILED",
                "symbols": ["BTCUSDT"],
            },
            {
                "name": "NEUTRAL_2023",
                "start": "2023-01-01",
                "end": "2023-12-31",
                "status": "PENDING",
                "symbols": ["BTCUSDT"],
            },
            {
                "name": "BULL_2024",
                "start": "2024-01-01",
                "end": "2024-12-31",
                "status": "PENDING",
                "symbols": ["BTCUSDT"],
            },
            {
                "name": "RECENT_2026",
                "start": "2026-01-01",
                "end": "2026-02-15",
                "status": "PENDING",
                "symbols": ["BTCUSDT"],
            },
        ]
        report = self._build_source_report(
            "unit_rerun_partial_src", windows, ["BULL_2021_H1", "BEAR_2022"]
        )
        cfg = self.tmp / "windows_partial.json"
        cfg.write_text(
            json.dumps(
                [
                    {"name": w["name"], "start": w["start"], "end": w["end"]}
                    for w in windows
                ]
            ),
            encoding="utf-8",
        )

        cp = self._run_rerun(report, cfg)
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn(
            "RERUN_SELECTION total_windows=5 selected_failed_windows=2", cp.stdout
        )

        rerun = json.loads(self.rerun_json.read_text(encoding="utf-8"))
        self.assertEqual(rerun["completed"], 2)
        self.assertEqual(rerun["total"], 5)
        self.assertEqual(rerun["failed"], 0)
        self.assertEqual(len(rerun.get("base_failed_windows", [])), 2)
        self.assertEqual(len(rerun.get("rerun_commands", [])), 2)
        self.assertIn("BULL_2021_H1", [c["window"] for c in rerun["rerun_commands"]])

        latest = json.loads(self.latest_json.read_text(encoding="utf-8"))
        self.assertEqual(latest["run_id"], "sentinel_full_suite")

    def test_complete_rerun_still_updates_rerun_latest_only(self):
        windows = [
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
                "status": "FAILED",
                "symbols": ["BTCUSDT"],
            },
        ]
        report = self._build_source_report(
            "unit_rerun_complete_src", windows, ["BULL_2021_H1", "BEAR_2022"]
        )
        cfg = self.tmp / "windows_complete.json"
        cfg.write_text(
            json.dumps(
                [
                    {"name": w["name"], "start": w["start"], "end": w["end"]}
                    for w in windows
                ]
            ),
            encoding="utf-8",
        )

        cp = self._run_rerun(report, cfg)
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn(
            "RERUN_SELECTION total_windows=2 selected_failed_windows=2", cp.stdout
        )

        rerun = json.loads(self.rerun_json.read_text(encoding="utf-8"))
        self.assertEqual(rerun["completed"], 2)
        self.assertEqual(rerun["total"], 2)
        self.assertEqual(rerun["failed"], 0)
        self.assertEqual(len(rerun.get("rerun_commands", [])), 2)
        self.assertTrue(
            all(c["command"].startswith("bash ") for c in rerun["rerun_commands"])
        )

        latest = json.loads(self.latest_json.read_text(encoding="utf-8"))
        self.assertEqual(latest["run_id"], "sentinel_full_suite")

        rerun_run_id = re.search(r"rerun_run_id=([^ ]+)", cp.stdout).group(1)
        run_report = json.loads(
            (self.walkforward / rerun_run_id / "walkforward.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            run_report["latest_warning_reason"], "RERUN_NEVER_UPDATES_LATEST_BY_POLICY"
        )


if __name__ == "__main__":
    unittest.main()
