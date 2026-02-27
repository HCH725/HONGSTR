import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_worker_pack_files_exist_and_executable() -> None:
    required_scripts = [
        REPO_ROOT / "scripts/worker_pack_bootstrap.sh",
        REPO_ROOT / "scripts/worker_run_research.sh",
        REPO_ROOT / "scripts/worker_run_backtests.sh",
    ]
    required_docs = [
        REPO_ROOT / "docs/ops/worker_pack.md",
        REPO_ROOT / "docs/ops/worker_pack_launchd.md",
    ]

    for path in required_scripts + required_docs:
        assert path.exists(), f"missing required worker pack file: {path}"

    for script in required_scripts:
        assert os.access(script, os.X_OK), f"script must be executable: {script}"


def test_worker_pack_doc_mentions_worker_state_contract() -> None:
    doc = (REPO_ROOT / "docs/ops/worker_pack.md").read_text(encoding="utf-8")
    assert "_local/worker_state/worker_heartbeat.json" in doc
    assert "_local/worker_state/last_run_research.json" in doc
    assert "_local/worker_state/last_run_backtests.json" in doc

    inventory = (REPO_ROOT / "docs/inventory.md").read_text(encoding="utf-8")
    assert "[Worker Pack (macOS-only)](docs/ops/worker_pack.md) **(Primary)**" in inventory


def test_no_data_paths_staged() -> None:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    data_lines = [line for line in proc.stdout.splitlines() if len(line) > 3 and line[3:].startswith("data/")]
    assert not data_lines, f"data/** must not be staged or tracked in worker pack changes: {data_lines}"
