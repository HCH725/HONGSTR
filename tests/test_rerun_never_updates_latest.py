import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRerunNeverUpdatesLatest(unittest.TestCase):
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

        sentinel = {"run_id": "full_suite_sentinel", "status": "COMPLETED"}
        self.latest_json.write_text(json.dumps(sentinel), encoding="utf-8")
        self.latest_md.write_text("# full suite sentinel\n", encoding="utf-8")
        self.before_json = self.latest_json.read_text(encoding="utf-8")
        self.before_md = self.latest_md.read_text(encoding="utf-8")

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
        src_run = self.walkforward / "rerun_never_updates_src"
        src_run.mkdir(parents=True, exist_ok=True)
        self.report = src_run / "walkforward.json"
        self.report.write_text(
            json.dumps(
                {
                    "run_id": "rerun_never_updates_src",
                    "windows": [
                        {
                            "name": "W1",
                            "start": "2026-02-14",
                            "end": "2026-02-15",
                            "status": "FAILED",
                            "symbols": ["BTCUSDT"],
                        },
                        {
                            "name": "W2",
                            "start": "2026-02-16",
                            "end": "2026-02-17",
                            "status": "FAILED",
                            "symbols": ["BTCUSDT"],
                        },
                    ],
                    "failed_windows_summary": [
                        {"name": "W1", "status": "FAILED", "error": "x"},
                        {"name": "W2", "status": "FAILED", "error": "x"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_rerun_does_not_overwrite_walkforward_latest(self):
        cp = subprocess.run(
            [
                "bash",
                "scripts/rerun_failed_windows.sh",
                "--report_json",
                str(self.report),
                "--config",
                str(self.config),
                "--runner_script",
                str(self.runner),
                "--reports_dir",
                str(self.reports),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertIn("RERUN_LATEST updated", cp.stdout)

        after_json = self.latest_json.read_text(encoding="utf-8")
        after_md = self.latest_md.read_text(encoding="utf-8")
        self.assertEqual(after_json, self.before_json)
        self.assertEqual(after_md, self.before_md)


if __name__ == "__main__":
    unittest.main()
