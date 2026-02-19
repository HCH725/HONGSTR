import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestWalkforwardSuiteEnsureHook(unittest.TestCase):
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

        self.marker = self.tmp / "ensure_called.marker"
        self.ensure_script = self.tmp / "fake_ensure.sh"
        self.ensure_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"echo called > '{self.marker}'\n",
            encoding="utf-8",
        )
        self.ensure_script.chmod(0o755)

        self.runner_script = self.tmp / "fake_runner.sh"
        self.runner_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "OUT_DIR=\"$(mktemp -d /tmp/hongstr_suite_hook_XXXX)\"\n"
            "echo '{\"results\":{\"overall\":{\"pass\":true}}}' > \"$OUT_DIR/gate.json\"\n"
            "echo '{\"decision\":\"HOLD\"}' > \"$OUT_DIR/selection.json\"\n"
            "echo \"OUT_DIR: $OUT_DIR\"\n"
            "echo \"LOG: /tmp/fake_suite_hook.log\"\n",
            encoding="utf-8",
        )
        self.runner_script.chmod(0o755)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_quick_mode_calls_ensure_hook(self):
        cp = subprocess.run(
            [
                "bash",
                "scripts/walkforward_suite.sh",
                "--quick",
                "--config",
                str(self.config),
                "--symbols",
                "BTCUSDT",
                "--runner_script",
                str(self.runner_script),
                "--ensure_script",
                str(self.ensure_script),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(cp.returncode, 0, msg=cp.stdout + "\n" + cp.stderr)
        self.assertTrue(self.marker.exists(), msg=cp.stdout + "\n" + cp.stderr)


if __name__ == "__main__":
    unittest.main()
