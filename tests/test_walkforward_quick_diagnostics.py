import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestWalkforwardQuickDiagnostics(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo_root = Path(__file__).resolve().parents[1]
        scripts_src = self.repo_root / "scripts"
        (self.tmp / "scripts").symlink_to(scripts_src)
        self.runner = self.tmp / "fake_runner.sh"
        self.runner.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env bash",
                    "set -euo pipefail",
                    'echo "Insufficient data for resampling"',
                    'echo "OUT_DIR: NA"',
                    'echo "LOG: /tmp/fake.log"',
                    "exit 1",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        self.runner.chmod(0o755)
        self.config = self.tmp / "windows.json"
        self.config.write_text(
            json.dumps(
                [
                    {"name": "W1", "start": "2021-01-01", "end": "2021-06-01"},
                    {"name": "W2", "start": "2022-01-01", "end": "2022-06-01"},
                    {"name": "W3", "start": "2023-01-01", "end": "2023-06-01"},
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_quick_mode_generates_insufficient_data_diagnostics(self):
        cp = subprocess.run(
            [
                "bash",
                "scripts/walkforward_suite.sh",
                "--quick",
                "--config",
                str(self.config),
                "--runner_script",
                str(self.runner),
                "--symbols",
                "BTCUSDT",
            ],
            cwd=self.tmp,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(cp.returncode, 0)
        m = re.search(r"Run ID:\s*([^\s]+)", cp.stdout)
        self.assertIsNotNone(m, msg=cp.stdout + "\n" + cp.stderr)
        run_id = m.group(1)
        diag_json = self.tmp / "reports" / "walkforward" / run_id / "failure_diagnostics.json"
        self.assertTrue(diag_json.exists())
        payload = json.loads(diag_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["reason_token"], "QUICK_SKIPPED_INSUFFICIENT_LOCAL_DATA")
        self.assertEqual(payload["run_mode"], "QUICK")
        self.assertGreaterEqual(len(payload["failures"]), 1)
        first = payload["failures"][0]
        self.assertEqual(first["reason_code"], "INSUFFICIENT_DATA_RESAMPLE")
        self.assertIn("required_start", first)
        self.assertIn("required_end", first)
        self.assertIn("local_cache_path_checked", first)


if __name__ == "__main__":
    unittest.main()
