from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "obsidian_mirror_run.sh"


def _write_script(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _run_wrapper(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    merged_env.update(env)
    return subprocess.run(
        ["bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=merged_env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_exporter_failure_does_not_block_mirror(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.log"
    exporter = tmp_path / "exporter.sh"
    mirror = tmp_path / "mirror.sh"

    _write_script(
        exporter,
        "#!/usr/bin/env bash\nset -e\nprintf 'exporter\\n' >> \"$TRACE_FILE\"\nexit 7\n",
    )
    _write_script(
        mirror,
        "#!/usr/bin/env bash\nset -e\nprintf 'mirror\\n' >> \"$TRACE_FILE\"\nexit 0\n",
    )

    result = _run_wrapper(
        {
            "TRACE_FILE": str(trace_file),
            "OBSIDIAN_DASHBOARDS_EXPORT_SCRIPT": str(exporter),
            "OBSIDIAN_MIRROR_PUBLISH_SCRIPT": str(mirror),
            "DASHBOARDS_EXPORT_ENABLED": "1",
        }
    )

    assert result.returncode == 0
    assert trace_file.read_text(encoding="utf-8").splitlines() == ["exporter", "mirror"]
    assert "WARN com.hongstr.obsidian_mirror_run: exporter_failed" in result.stderr


def test_exporter_skip_when_disabled(tmp_path: Path) -> None:
    trace_file = tmp_path / "trace.log"
    exporter = tmp_path / "exporter.sh"
    mirror = tmp_path / "mirror.sh"

    _write_script(
        exporter,
        "#!/usr/bin/env bash\nset -e\nprintf 'exporter\\n' >> \"$TRACE_FILE\"\nexit 0\n",
    )
    _write_script(
        mirror,
        "#!/usr/bin/env bash\nset -e\nprintf 'mirror\\n' >> \"$TRACE_FILE\"\nexit 0\n",
    )

    result = _run_wrapper(
        {
            "TRACE_FILE": str(trace_file),
            "OBSIDIAN_DASHBOARDS_EXPORT_SCRIPT": str(exporter),
            "OBSIDIAN_MIRROR_PUBLISH_SCRIPT": str(mirror),
            "DASHBOARDS_EXPORT_ENABLED": "0",
        }
    )

    assert result.returncode == 0
    assert trace_file.read_text(encoding="utf-8").splitlines() == ["mirror"]
    assert "INFO com.hongstr.obsidian_mirror_run: exporter_skipped" in result.stdout
