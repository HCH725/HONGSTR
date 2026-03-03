import importlib.util
import os
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/watchdog_status_snapshot.py"


def _load_watchdog_module():
    spec = importlib.util.spec_from_file_location("watchdog_status_snapshot_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_build_watchdog_snapshot_schema_is_stable(tmp_path: Path):
    mod = _load_watchdog_module()
    log_path = tmp_path / "tg_cp_watchdog.out.log"
    log_path.write_text("OK: heartbeat age_sec=2823\n", encoding="utf-8")
    os.utime(log_path, (1700000000, 1700000000))

    sample_output = """gui/501/com.hongstr.tg_cp_watchdog = {
\tactive count = 0
\tpath = /Users/hong/Library/LaunchAgents/com.hongstr.tg_cp_watchdog.plist
\ttype = LaunchAgent
\tstate = not running

\tprogram = /bin/bash
\tstdout path = /Users/hong/Library/Logs/hongstr/tg_cp_watchdog.out.log
\tstderr path = /Users/hong/Library/Logs/hongstr/tg_cp_watchdog.err.log
\truns = 4
\tlast exit code = 0
\trun interval = 120 seconds
}
"""

    def runner(args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=sample_output, stderr="")

    snapshot = mod.build_watchdog_snapshot(
        uid=501,
        label="com.hongstr.tg_cp_watchdog",
        log_path=log_path,
        now_ts=1700000300.0,
        runner=runner,
    )

    assert list(snapshot.keys()) == list(mod.TOP_LEVEL_KEYS)
    assert list(snapshot["launchctl"].keys()) == [
        "ok",
        "target",
        "state",
        "active_count",
        "runs",
        "last_exit_code",
        "path",
        "stdout_path",
        "stderr_path",
        "program",
        "run_interval_seconds",
        "command_return_code",
        "command_stderr",
    ]
    assert list(snapshot["last_check"].keys()) == [
        "log_path",
        "exists",
        "last_line",
        "line_status",
        "line_reason",
        "updated_at_utc",
        "age_sec",
        "expected_within_sec",
    ]
    assert list(snapshot["sources"].keys()) == ["launchctl_command", "log_path", "output_path"]
    assert snapshot["schema_version"] == mod.SCHEMA_VERSION
    assert snapshot["status"] == "OK"
    assert snapshot["status_reason"] == "launchctl_idle_timer"
    assert snapshot["launchctl_target"] == "gui/501/com.hongstr.tg_cp_watchdog"
    assert snapshot["launchctl"]["run_interval_seconds"] == 120
    assert snapshot["launchctl"]["last_exit_code"] == 0
    assert snapshot["launchctl"]["command_return_code"] == 0
    assert snapshot["last_check"]["exists"] is True
    assert snapshot["last_check"]["last_line"] == "OK: heartbeat age_sec=2823"
    assert snapshot["last_check"]["line_status"] == "OK"
    assert snapshot["last_check"]["line_reason"] == "heartbeat age_sec=2823"
    assert snapshot["last_check"]["age_sec"] == 300
    assert snapshot["last_check"]["expected_within_sec"] == 600
    assert snapshot["sources"]["launchctl_command"] == "launchctl print gui/501/com.hongstr.tg_cp_watchdog"
