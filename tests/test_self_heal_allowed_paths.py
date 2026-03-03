import importlib.util
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/self_heal/enforce_allowed_paths.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("self_heal_allowed_paths_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_is_allowed_supports_files_dirs_and_globs():
    mod = _load_module()

    assert mod._is_allowed(".github/workflows/self_heal.yml", ".github/workflows/self_heal.yml")
    assert mod._is_allowed("scripts/self_heal/enforce_allowed_paths.py", "scripts/self_heal/")
    assert mod._is_allowed("scripts/self_heal/enforce_allowed_paths.py", "scripts/self_heal/**")
    assert mod._is_allowed("tests/test_self_heal_allowed_paths.py", "tests/test_*.py")

    assert not mod._is_allowed("src/hongstr/app.py", "scripts/self_heal/")
    assert not mod._is_allowed("data/state/foo.json", "scripts/**")


def test_collect_changed_paths_prefers_worktree_and_falls_back(monkeypatch):
    mod = _load_module()
    responses = {
        ("diff", "--name-only", "--cached"): ["scripts/self_heal/enforce_allowed_paths.py"],
        ("diff", "--name-only"): ["tests/test_self_heal_allowed_paths.py"],
        ("ls-files", "--others", "--exclude-standard"): ["tmp/generated.diff"],
        ("diff", "--name-only", "HEAD~1..HEAD"): [".github/workflows/self_heal.yml"],
    }

    def fake_run_git_name_only(args):
        return list(responses[tuple(args)])

    monkeypatch.setattr(mod, "_run_git_name_only", fake_run_git_name_only)
    assert mod._collect_changed_paths() == [
        "scripts/self_heal/enforce_allowed_paths.py",
        "tests/test_self_heal_allowed_paths.py",
        "tmp/generated.diff",
    ]

    def fake_run_git_name_only_fallback(args):
        if tuple(args) == ("diff", "--name-only", "HEAD~1..HEAD"):
            return [".github/workflows/self_heal.yml"]
        raise subprocess.CalledProcessError(returncode=1, cmd=["git", *args])

    monkeypatch.setattr(mod, "_run_git_name_only", fake_run_git_name_only_fallback)
    assert mod._collect_changed_paths() == [".github/workflows/self_heal.yml"]
