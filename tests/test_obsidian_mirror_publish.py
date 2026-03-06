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

    _write(source_vault / "KB" / "PR" / "PR-0001.md", "ok\n")
    _write(source_vault / "KB" / "raw" / "private.txt", "must_not_sync\n")
    _write(source_vault / "KB" / "cache" / "tmp.txt", "must_not_sync\n")
    _write(source_vault / "KB" / "state" / "state.json", "must_not_sync\n")
    _write(source_vault / "Dashboards" / "overview.md", "dashboard\n")
    _write(source_vault / "Dashboards" / ".obsidian" / "workspace.json", "workspace\n")
    _write(source_vault / "Dashboards" / ".obsidian" / "notehistory.log", "history\n")
    _write(source_vault / "Daily" / "2026-03-05.md", "not_in_whitelist\n")

    result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(primary_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
            "OBSIDIAN_MIRROR_LOCK_DIR": str(tmp_path / "mirror.lock"),
        }
    )

    assert result.returncode == 0, result.stderr
    assert (target_vault / "KB" / "PR" / "PR-0001.md").exists()
    assert (target_vault / "Dashboards" / "overview.md").exists()
    assert not (target_vault / "KB" / "raw" / "private.txt").exists()
    assert not (target_vault / "KB" / "cache" / "tmp.txt").exists()
    assert not (target_vault / "KB" / "state" / "state.json").exists()
    assert not (target_vault / "Dashboards" / ".obsidian" / "workspace.json").exists()
    assert not (target_vault / "Dashboards" / ".obsidian" / "notehistory.log").exists()
    assert not (target_vault / "Daily" / "2026-03-05.md").exists()


def test_mirror_non_blocking_on_missing_source(tmp_path: Path) -> None:
    missing_source_root = tmp_path / "does_not_exist"
    target_root = tmp_path / "icloud_obsidian_root"

    result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(missing_source_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
            "OBSIDIAN_MIRROR_LOCK_DIR": str(tmp_path / "mirror.lock"),
        }
    )

    assert result.returncode == 0
    assert "primary_vault_not_found" in result.stderr


def test_strict_mirror_delete_is_gated(tmp_path: Path) -> None:
    primary_root = tmp_path / "primary_vaults"
    source_vault = primary_root / "HONGSTR"
    target_root = tmp_path / "icloud_obsidian_root"
    target_vault = target_root / "HONGSTR_MIRROR"

    _write(source_vault / "KB" / "PR" / "PR-1000.md", "canonical\n")
    _write(target_vault / "KB" / "PR" / "PR-1000.md", "stale\n")
    _write(target_vault / "KB" / "PR" / "EXTRA.md", "extra\n")

    safe_result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(primary_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
            "STRICT_MIRROR": "0",
            "OBSIDIAN_MIRROR_LOCK_DIR": str(tmp_path / "mirror.lock"),
        }
    )
    assert safe_result.returncode == 0, safe_result.stderr
    assert (target_vault / "KB" / "PR" / "EXTRA.md").exists()
    assert (target_vault / "KB" / "PR" / "PR-1000.md").read_text(encoding="utf-8") == "canonical\n"

    strict_result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(primary_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
            "STRICT_MIRROR": "1",
            "OBSIDIAN_MIRROR_LOCK_DIR": str(tmp_path / "mirror.lock"),
        }
    )
    assert strict_result.returncode == 0, strict_result.stderr
    assert not (target_vault / "KB" / "PR" / "EXTRA.md").exists()


def test_dry_run_does_not_modify_target(tmp_path: Path) -> None:
    primary_root = tmp_path / "primary_vaults"
    source_vault = primary_root / "HONGSTR"
    target_root = tmp_path / "icloud_obsidian_root"
    target_vault = target_root / "HONGSTR_MIRROR"

    _write(source_vault / "KB" / "PR" / "PR-2000.md", "from_source\n")
    _write(target_vault / "KB" / "PR" / "PR-2000.md", "old_target\n")
    _write(target_vault / "KB" / "PR" / "EXTRA.md", "extra\n")

    result = _run_mirror(
        {
            "OBSIDIAN_PRIMARY_ROOT": str(primary_root),
            "ICLOUD_OBSIDIAN_ROOT": str(target_root),
            "ICLOUD_VAULT_NAME": "HONGSTR_MIRROR",
            "MIRROR_ENABLED": "1",
            "STRICT_MIRROR": "1",
            "DRY_RUN": "1",
            "OBSIDIAN_MIRROR_LOCK_DIR": str(tmp_path / "mirror.lock"),
        }
    )

    assert result.returncode == 0, result.stderr
    assert (target_vault / "KB" / "PR" / "EXTRA.md").exists()
    assert (target_vault / "KB" / "PR" / "PR-2000.md").read_text(encoding="utf-8") == "old_target\n"
