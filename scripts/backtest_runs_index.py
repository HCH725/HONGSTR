#!/usr/bin/env python3
"""
Read-only helpers for discovering backtest run artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from discovery_utils import read_json_file, repo_relative_path
except ImportError:  # pragma: no cover - package import fallback
    from scripts.discovery_utils import read_json_file, repo_relative_path

INDEX_PATH = Path("data/state/backtest_runs_index_latest.json")
BACKTEST_ROOT = Path("data/backtests")
ARTIFACT_FILENAMES = ("summary.json", "gate.json", "leaderboard.json")


def _resolve_repo_path(path_value: str, repo_root: Path) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _candidate_from_index_row(row: dict[str, Any], repo_root: Path) -> dict[str, Any] | None:
    summary_path_raw = row.get("summary_path")
    if not isinstance(summary_path_raw, str) or not summary_path_raw.strip():
        return None

    summary_path = _resolve_repo_path(summary_path_raw, repo_root)
    run_dir = summary_path.parent
    if not run_dir.exists():
        return None

    return {
        "run_id": row.get("run_id"),
        "run_dir": run_dir,
        "summary_path": summary_path,
        "gate_path": run_dir / "gate.json",
        "leaderboard_path": run_dir / "leaderboard.json",
        "ts_utc": row.get("ts_utc"),
        "strategy": row.get("strategy"),
        "timeframe": row.get("timeframe"),
        "regime": row.get("regime"),
    }


def _discover_from_index(repo_root: Path) -> tuple[list[dict[str, Any]], list[str]] | None:
    payload = read_json_file(repo_root / INDEX_PATH)
    if not isinstance(payload, dict):
        return None

    rows = payload.get("rows")
    if not isinstance(rows, list):
        return None

    candidates: list[dict[str, Any]] = []
    seen_dirs: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidate = _candidate_from_index_row(row, repo_root)
        if candidate is None:
            continue
        key = candidate["run_dir"].resolve().as_posix()
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        candidates.append(candidate)

    if not candidates:
        return None
    return candidates, [INDEX_PATH.as_posix()]


def _discover_from_glob(repo_root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    run_map: dict[str, dict[str, Any]] = {}
    backtest_root = repo_root / BACKTEST_ROOT
    if not backtest_root.exists():
        return [], []

    for artifact_name in ARTIFACT_FILENAMES:
        for artifact_path in sorted(backtest_root.rglob(artifact_name)):
            run_key = artifact_path.parent.resolve().as_posix()
            candidate = run_map.setdefault(
                run_key,
                {
                    "run_id": artifact_path.parent.name,
                    "run_dir": artifact_path.parent.resolve(),
                    "summary_path": artifact_path.parent / "summary.json",
                    "gate_path": artifact_path.parent / "gate.json",
                    "leaderboard_path": artifact_path.parent / "leaderboard.json",
                    "_sort_mtime": 0.0,
                },
            )
            try:
                candidate["_sort_mtime"] = max(candidate["_sort_mtime"], artifact_path.stat().st_mtime)
            except Exception:
                pass

    ordered = sorted(
        run_map.values(),
        key=lambda row: (float(row.get("_sort_mtime", 0.0) or 0.0), row["run_dir"].as_posix()),
        reverse=True,
    )
    for row in ordered:
        row.pop("_sort_mtime", None)
    return ordered, []


def discover_backtest_candidates(repo_root: Path | None = None) -> tuple[list[dict[str, Any]], str, list[str]]:
    root = repo_root.resolve() if repo_root is not None else Path(".").resolve()

    indexed = _discover_from_index(root)
    if indexed is not None:
        candidates, source_inputs = indexed
        return candidates, "index", source_inputs

    candidates, source_inputs = _discover_from_glob(root)
    return candidates, "glob", source_inputs


def main() -> int:
    repo_root = Path(".").resolve()
    candidates, source, source_inputs = discover_backtest_candidates(repo_root)
    payload = {
        "candidates_source": source,
        "rows": [
            {
                "run_id": row.get("run_id"),
                "run_dir": repo_relative_path(row["run_dir"], repo_root),
                "summary_path": repo_relative_path(row["summary_path"], repo_root),
                "gate_path": repo_relative_path(row["gate_path"], repo_root),
                "leaderboard_path": repo_relative_path(row["leaderboard_path"], repo_root),
            }
            for row in candidates
        ],
        "source_inputs": source_inputs,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
