#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.loop.report_only_research_skills import backtest_repro_gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a report-only backtest repro gate artifact.")
    parser.add_argument("--candidate-id", default="", help="Candidate id to pin in the report.")
    parser.add_argument("--slice-ref", default="", help="Fixed regime slice reference, e.g. BEAR@4h.")
    parser.add_argument("--code-ref", default="", help="Fixed code ref to pin in the report.")
    parser.add_argument("--runs", type=int, default=3, help="Number of comparison runs to report.")
    parser.add_argument(
        "--summary-path",
        default="",
        help="Explicit summary artifact path to use as baseline. Defaults to /daily latest_backtest_head summary.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/research/repro_gate",
        help="Artifact output directory relative to repo root.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Build the payload without writing JSON/Markdown artifacts.",
    )
    args = parser.parse_args()

    repo_root = REPO_ROOT
    payload = backtest_repro_gate(
        repo_root,
        candidate_id=args.candidate_id,
        slice_ref=args.slice_ref,
        code_ref=args.code_ref,
        runs=args.runs,
        summary_path=args.summary_path,
        write_artifacts=not args.no_write,
        output_dir=args.output_dir,
    )
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
