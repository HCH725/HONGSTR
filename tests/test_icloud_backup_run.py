from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "icloud_backup_run.sh"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_backup(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
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


def test_backup_writes_latest_and_snapshot_and_excludes_secrets(tmp_path: Path) -> None:
    fake_repo = tmp_path / "repo"
    backup_root = tmp_path / "backup"
    snapshot_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    _write(fake_repo / "scripts" / "run.sh", "echo ok\n")
    _write(fake_repo / "docs" / "guide.md", "# guide\n")
    _write(fake_repo / "launchd" / "job.plist", "<plist></plist>\n")
    _write(fake_repo / "web" / "index.html", "<html></html>\n")
    _write(fake_repo / "_local" / "obsidian_vault" / "HONGSTR" / "KB" / "daily.md", "daily\n")
    _write(fake_repo / "_local" / "obsidian_vault" / "HONGSTR" / "Dashboards" / "10-HealthPack.md", "dash\n")
    _write(fake_repo / "data" / "state" / "system_health_latest.json", "{\"ssot_status\":\"OK\"}\n")
    _write(fake_repo / "reports" / "state_atomic" / "watchdog_status_latest.json", "{\"status\":\"OK\"}\n")
    _write(fake_repo / "data" / "derived" / "BTCUSDT" / "1m" / "klines.jsonl", "{}\n")
    _write(fake_repo / "data" / "backtests" / "2026-03-05" / "summary.json", "{}\n")

    _write(fake_repo / "docs" / ".env", "SECRET=1\n")
    _write(fake_repo / "scripts" / "token.txt", "secret-token\n")
    _write(fake_repo / "launchd" / "id_rsa", "private-key\n")
    _write(fake_repo / ".git" / "config", "[core]\n")
    _write(fake_repo / "node_modules" / "pkg" / "index.js", "module.exports={}\n")
    _write(fake_repo / ".venv" / "bin" / "python", "python\n")

    result = _run_backup(
        {
            "HONGSTR_REPO_ROOT": str(fake_repo),
            "BACKUP_ROOT": str(backup_root),
            "BACKUP_ENABLED": "1",
            "BACKUP_MODE": "full",
            "BACKUP_RETENTION_DAYS": "0",
        }
    )

    assert result.returncode == 0, result.stderr

    latest_root = backup_root / "latest"
    snapshot_root = backup_root / "snapshots" / snapshot_day

    assert (latest_root / "scripts" / "run.sh").exists()
    assert (latest_root / "docs" / "guide.md").exists()
    assert (latest_root / "launchd" / "job.plist").exists()
    assert (latest_root / "web" / "index.html").exists()
    assert (latest_root / "_local" / "obsidian_vault" / "HONGSTR" / "KB" / "daily.md").exists()
    assert (latest_root / "_local" / "obsidian_vault" / "HONGSTR" / "Dashboards" / "10-HealthPack.md").exists()
    assert (latest_root / "data" / "state" / "system_health_latest.json").exists()
    assert (latest_root / "reports" / "state_atomic" / "watchdog_status_latest.json").exists()
    assert (latest_root / "data" / "derived" / "BTCUSDT" / "1m" / "klines.jsonl").exists()
    assert (latest_root / "data" / "backtests" / "2026-03-05" / "summary.json").exists()

    assert (snapshot_root / "scripts" / "run.sh").exists()
    assert (snapshot_root / "docs" / "guide.md").exists()

    assert not (latest_root / "docs" / ".env").exists()
    assert not (latest_root / "scripts" / "token.txt").exists()
    assert not (latest_root / "launchd" / "id_rsa").exists()
    assert not (latest_root / ".git" / "config").exists()
    assert not (latest_root / "node_modules" / "pkg" / "index.js").exists()
    assert not (latest_root / ".venv" / "bin" / "python").exists()

    manifest = json.loads((latest_root / "manifest.json").read_text(encoding="utf-8"))
    assert isinstance(manifest.get("ts_utc"), str)
    assert manifest.get("mode") == "full"
    assert isinstance(manifest.get("counts"), dict)
    assert "files" in manifest["counts"]
    assert "bytes" in manifest
    assert manifest.get("source_root") == str(fake_repo)
    assert manifest.get("target_root") == str(latest_root)
    assert isinstance(manifest.get("excludes_summary"), list)

    sha_lines = (latest_root / "sha256sums.txt").read_text(encoding="utf-8")
    assert "manifest.json" in sha_lines


def test_backup_dry_run_does_not_write_artifacts(tmp_path: Path) -> None:
    fake_repo = tmp_path / "repo"
    backup_root = tmp_path / "backup"
    _write(fake_repo / "scripts" / "run.sh", "echo ok\n")

    result = _run_backup(
        {
            "HONGSTR_REPO_ROOT": str(fake_repo),
            "BACKUP_ROOT": str(backup_root),
            "BACKUP_ENABLED": "1",
            "BACKUP_DRY_RUN": "1",
        }
    )

    assert result.returncode == 0, result.stderr
    latest_root = backup_root / "latest"
    assert not (latest_root / "manifest.json").exists()
    assert not (latest_root / "sha256sums.txt").exists()
