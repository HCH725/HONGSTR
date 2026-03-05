from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "disable_noisy_jobs.sh"


def test_disable_noisy_jobs_script_is_valid_bash() -> None:
    completed = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr


def test_disable_noisy_jobs_targets_expected_labels() -> None:
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "com.hongstr.obsidian_daily" in text
    assert "com.hongstr.kb_sync" in text
    assert "print-disabled" in text
