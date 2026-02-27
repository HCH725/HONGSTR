import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("/Users/hong/Projects/HONGSTR/scripts/auto_pr_utils.py")


def _run(args, stdin_text=""):
    cmd = [sys.executable, str(SCRIPT), *args]
    proc = subprocess.run(cmd, input=stdin_text, text=True, capture_output=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_allowlist_check_passes_for_allowed_paths():
    rc, out, _ = _run(["check"], "docs/a.md\nresearch/loop/gates.py\nscripts/auto_pr.sh\n")
    assert rc == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["bad_paths"] == []


def test_allowlist_check_blocks_core_paths():
    rc, out, _ = _run(["check"], "src/hongstr/execution/core.py\n")
    assert rc == 2
    payload = json.loads(out)
    assert payload["ok"] is False
    assert "src/hongstr/execution/core.py" in payload["bad_paths"]


def test_classify_docs_only_title():
    rc, out, _ = _run(["classify"], "docs/ops_auto_pr.md\n")
    assert rc == 0
    payload = json.loads(out)
    assert payload["kind"] == "docs-only"
    assert payload["title"].startswith("docs")


def test_classify_research_docs_combo():
    rc, out, _ = _run(["classify"], "docs/governance/overfit_gates_aggressive.md\nresearch/loop/gates.py\n")
    assert rc == 0
    payload = json.loads(out)
    assert payload["kind"] == "research-docs"


def test_render_pr_body_never_executes_path_like_tokens():
    stdin_paths = "docs/architecture\nsrc/hongstr/__init__.py\nreport_only\n"
    rc, out, err = _run(
        ["render-pr-body", "--title", "ops(auto_pr): allowlisted mixed update", "--preflight-text", "ok"],
        stdin_paths,
    )
    assert rc == 0
    assert err == ""
    assert "- `docs/architecture`" in out
    assert "- `src/hongstr/__init__.py`" in out
    assert "- `report_only`" in out
    assert "is a directory" not in out
    assert "Permission denied" not in out
    assert "command not found" not in out
