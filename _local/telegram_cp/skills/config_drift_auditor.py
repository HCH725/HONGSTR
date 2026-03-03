from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

# Use gitpython for plumbing (no shell exec in tg_cp)
try:
    import git
except ImportError:
    git = None


DEFAULT_ALLOWLIST = [
    ".env.example",
    "_local/telegram_cp/skills_registry.json",
    "_local/telegram_cp/policy.json",
    "scripts/refresh_state.sh",
]


def audit_config_drift(repo_path: Path, baseline_ref: str, paths: str | list[str] | None = None) -> dict[str, Any]:
    """
    Audit configuration drift between a baseline SHA and the current working tree.
    Returns structured results + markdown summary.
    """
    if not git:
        return {
            "status": "UNKNOWN",
            "markdown": "❌ GitPython not installed. Cannot perform drift audit.",
            "data": {"error": "GitPython missing"}
        }

    if not baseline_ref or len(baseline_ref) < 7:
        return {
            "status": "UNKNOWN",
            "markdown": "⚠️ Invalid baseline_ref. Must be a full SHA or valid branch name.",
            "data": {"error": "invalid_ref"}
        }

    # Resolve paths
    if not paths:
        target_paths = DEFAULT_ALLOWLIST
    elif isinstance(paths, str):
        target_paths = [p.strip() for p in paths.split(",") if p.strip()]
    else:
        target_paths = paths

    try:
        repo = git.Repo(repo_path)
    except Exception as e:
        return {
            "status": "UNKNOWN",
            "markdown": f"❌ Failed to open repository: {e}",
            "data": {"error": str(e)}
        }

    try:
        baseline_commit = repo.commit(baseline_ref)
    except Exception as e:
        return {
            "status": "UNKNOWN",
            "markdown": f"⚠️ Baseline ref `{baseline_ref}` not found or unreadable: {e}",
            "data": {"error": "ref_not_found", "detail": str(e)}
        }

    drift_results = []
    total_files = 0
    drifted_files = 0

    for rel_path in target_paths:
        total_files += 1
        abs_path = repo_path / rel_path
        
        # 1. Get baseline content
        try:
            # gitpython tree lookup
            blob = baseline_commit.tree / rel_path
            baseline_content = blob.data_stream.read().decode("utf-8", "ignore")
        except KeyError:
            baseline_content = None # Not in baseline

        # 2. Get current content
        if abs_path.exists():
            try:
                current_content = abs_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                current_content = None
        else:
            current_content = None

        # 3. Handle cases
        if baseline_content is None and current_content is None:
            continue # Neither exists, skip

        if baseline_content == current_content:
            drift_results.append({
                "path": rel_path,
                "status": "MATCH",
                "diff": None
            })
            continue

        # Drift detected
        drifted_files += 1
        
        # Generate diff
        b_lines = baseline_content.splitlines(keepends=True) if baseline_content else []
        c_lines = current_content.splitlines(keepends=True) if current_content else []
        
        diff = "".join(difflib.unified_diff(
            b_lines, c_lines,
            fromfile=f"baseline/{rel_path}",
            tofile=f"current/{rel_path}",
            n=2
        ))
        
        drift_results.append({
            "path": rel_path,
            "status": "DRIFT",
            "diff": diff
        })

    # Summary Generation
    status = "OK" if drifted_files == 0 else "WARN"
    
    sections = [
        f"🔍 *Config Drift Audit* (`{baseline_ref[:8]}`)",
        f"Status: {status}",
        f"Files Audited: {total_files}",
        f"Drifted: {drifted_files}",
        ""
    ]

    if drifted_files > 0:
        sections.append("*Drifted Files:*")
        for res in drift_results:
            if res["status"] == "DRIFT":
                sections.append(f"• `{res['path']}`")
        
        sections.append("\nRun `git diff` manually if you need full details.")
    else:
        sections.append("✅ No drift detected in allowlisted paths.")

    return {
        "status": status,
        "report_only": True,
        "markdown": "\n".join(sections),
        "data": {
            "baseline": str(baseline_commit.hexsha),
            "total_files": total_files,
            "drifted_count": drifted_files,
            "results": drift_results
        }
    }
