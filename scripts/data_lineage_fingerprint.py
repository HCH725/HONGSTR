#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.loop.report_only_research_skills import data_lineage_fingerprint


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a report-only data lineage fingerprint artifact.")
    parser.add_argument(
        "--output-dir",
        default="reports/research/lineage",
        help="Artifact output directory relative to repo root.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Build the payload without writing JSON/Markdown artifacts.",
    )
    args = parser.parse_args()

    repo_root = REPO_ROOT
    payload = data_lineage_fingerprint(
        repo_root,
        write_artifacts=not args.no_write,
        output_dir=args.output_dir,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
