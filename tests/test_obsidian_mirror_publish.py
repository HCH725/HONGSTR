from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "obsidian_mirror_publish.sh"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_mirror(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
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


def test_mirror_whitelist_and_excludes(tmp_path: Path) -> None:
    primary_root = tmp_path / "primary_vaults"
    source_vault = primary_root / "HONGSTR"
    target_root = tmp_path / "icloud_obsidian_root"
    target_vault = target_root / "HONGSTR_MIRROR"

    _write(source_vault / "KB" / "_meta" / "kb_sync_state.json", "{ }\n")
    _write(source_vault / "KB" / "PR" / "PR-0001.md", "ok\n")
    _write(source_vault / "KB" / "Runbooks" / "mirror-contract.md", "runbook\n")
    _write(source_vault / "KB" / "Incidents" / "2026-03-07_test.md", "incident\n")
    _write(source_vault / "KB" / "Research-Summaries" / "oos-check.md", "research\n")
    _write(source_vault / "KB" / "SSOT" / "Daily" / "2026-03-04.md", "legacy\n")
    _write(source_vault / "KB" / "Scratch" / "notes.md", "out_of_contract\n")
    _write(source_vault / "KB" / "raw" / "private.txt", "must_not_sync\n")
    _write(source_vault / "KB" / "cache" / "tmp.txt", "must_not_sync\n")
    _write(source_vault / "KB" / "state" / "state.json", "must_not_sync\n")
    _write(source_vault / "Dashboards" / "overview.md", "dashboard\n")
    _write(source_vault / "Dashboards" / ".obsidian" / "workspace.json", "workspace\n")
    _write(source_vault / "Dashboards" / ".obsidian" / "notehistory.log", "history\n")
    _write(source_vault / "Daily" / "2026" / "03" / "2026-03-05.md", "daily\n")

    result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(primary_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
        }
    )

    assert result.returncode == 0, result.stderr
    assert "legacy_kb_ssot_present" in result.stderr
    assert (target_vault / "KB" / "_meta" / "kb_sync_state.json").exists()
    assert (target_vault / "KB" / "PR" / "PR-0001.md").exists()
    assert (target_vault / "KB" / "Runbooks" / "mirror-contract.md").exists()
    assert (target_vault / "KB" / "Incidents" / "2026-03-07_test.md").exists()
    assert (target_vault / "KB" / "Research-Summaries" / "oos-check.md").exists()
    assert (target_vault / "Dashboards" / "overview.md").exists()
    assert (target_vault / "Daily" / "2026" / "03" / "2026-03-05.md").exists()
    assert not (target_vault / "KB" / "SSOT" / "Daily" / "2026-03-04.md").exists()
    assert not (target_vault / "KB" / "Scratch" / "notes.md").exists()
    assert not (target_vault / "KB" / "raw" / "private.txt").exists()
    assert not (target_vault / "KB" / "cache" / "tmp.txt").exists()
    assert not (target_vault / "KB" / "state" / "state.json").exists()
    assert not (target_vault / "Dashboards" / ".obsidian" / "workspace.json").exists()
    assert not (target_vault / "Dashboards" / ".obsidian" / "notehistory.log").exists()


def test_mirror_non_blocking_on_missing_source(tmp_path: Path) -> None:
    missing_source_root = tmp_path / "does_not_exist"
    target_root = tmp_path / "icloud_obsidian_root"

    result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(missing_source_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
        }
    )

    assert result.returncode == 0
    assert "primary_vault_not_found" in result.stderr
