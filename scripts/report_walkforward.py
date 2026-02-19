import argparse
import json
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def load_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return None


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def atomic_write_json(path: Path, payload: dict) -> None:
    atomic_write_text(path, json.dumps(payload, indent=2))


def parse_suite_results(results_path: Path) -> List[dict]:
    rows: List[dict] = []
    if not results_path.exists():
        return rows

    with open(results_path, "r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) != 9:
                continue
            rows.append(
                {
                    "name": parts[0],
                    "start": parts[1],
                    "end": parts[2],
                    "status": parts[3],
                    "run_dir": parts[4] if parts[4] != "-" else None,
                    "gate_overall": parts[5],
                    "selection_decision": parts[6],
                    "failure_reason": parts[7] if parts[7] != "-" else "",
                    "symbols": parts[8].split(",")
                    if parts[8] and parts[8] != "-"
                    else [],
                }
            )
    return rows


def detect_latest_suite_run(reports_dir: Path) -> Tuple[Optional[str], Optional[Path]]:
    wf_root = reports_dir / "walkforward"
    candidates: List[Tuple[float, str, Path]] = []
    if not wf_root.exists():
        return None, None

    for run_dir in wf_root.iterdir():
        if not run_dir.is_dir():
            continue
        tsv_path = run_dir / "suite_results.tsv"
        if not tsv_path.exists():
            continue
        candidates.append((tsv_path.stat().st_mtime, run_dir.name, tsv_path))

    if not candidates:
        return None, None

    candidates.sort(reverse=True)
    _, run_id, tsv_path = candidates[0]
    return run_id, tsv_path


def is_latest_suite_run(reports_dir: Path, run_id: str) -> bool:
    latest_run_id, _ = detect_latest_suite_run(reports_dir)
    return bool(latest_run_id and latest_run_id == run_id)


def infer_regime(window_name: str) -> str:
    upper = window_name.upper()
    if "BULL" in upper:
        return "BULL"
    if "BEAR" in upper:
        return "BEAR"
    if "NEUTRAL" in upper:
        return "NEUTRAL"
    return "MIXED"


def build_report(
    config_windows: List[dict],
    suite_rows: List[dict],
    run_id: str,
    run_mode: str = "FULL",
    rerun_scope: str = "ALL_WINDOWS",
    suite_mode: str = "FULL_SUITE",
) -> dict:
    row_map: Dict[str, dict] = {row["name"]: row for row in suite_rows}
    report_windows: List[dict] = []
    regime_stats = defaultdict(list)

    for item in config_windows:
        name = item["name"]
        row = row_map.get(name)
        result = {
            "name": name,
            "start": item["start"],
            "end": item["end"],
            "status": "PENDING",
            "run_dir": None,
            "gate_overall": "UNKNOWN",
            "selection_decision": "UNKNOWN",
            "sharpe": None,
            "mdd": None,
            "total_return": None,
            "trades": None,
            "symbols": [],
            "failure_reason": "",
            "error": None,
        }

        if row:
            result["status"] = row["status"]
            result["run_dir"] = row["run_dir"]
            result["gate_overall"] = row["gate_overall"]
            result["selection_decision"] = row["selection_decision"]
            result["symbols"] = row["symbols"]
            result["failure_reason"] = row["failure_reason"]
            result["error"] = row["failure_reason"] or None

            if row["status"] == "COMPLETED" and row["run_dir"]:
                run_path = Path(row["run_dir"])
                summary = load_json(run_path / "summary.json")
                gate = load_json(run_path / "gate.json")
                selection = load_json(run_path / "selection.json")
                if gate:
                    gpass = gate.get("results", {}).get("overall", {}).get("pass")
                    result["gate_overall"] = "PASS" if gpass else "FAIL"
                if selection:
                    result["selection_decision"] = selection.get(
                        "decision", result["selection_decision"]
                    )
                if summary:
                    result["sharpe"] = summary.get("sharpe")
                    result["mdd"] = summary.get("max_drawdown")
                    result["total_return"] = summary.get("total_return")
                    result["trades"] = summary.get("trades_count")
                    if result["sharpe"] is not None:
                        regime_stats[infer_regime(name)].append(result["sharpe"])

        report_windows.append(result)

    completed = sum(1 for row in report_windows if row["status"] == "COMPLETED")
    failed_windows = [
        row for row in report_windows if row["status"] in {"FAILED", "ERROR"}
    ]
    failed = len(failed_windows)
    total = len(config_windows)

    if completed == total and failed == 0:
        overall_status = "COMPLETED"
    elif failed > 0:
        overall_status = "FAILED"
    else:
        overall_status = "PARTIAL"

    stability = {}
    for regime, values in regime_stats.items():
        values.sort()
        size = len(values)
        stability[regime] = {
            "count": size,
            "mean_sharpe": sum(values) / size,
            "min_sharpe": values[0],
            "max_sharpe": values[-1],
            "median_sharpe": values[size // 2],
        }

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        "run_mode": run_mode,
        "rerun_scope": rerun_scope,
        "suite_mode": suite_mode,
        "windows_selected": len(suite_rows),
        "status": overall_status,
        "windows_total": total,
        "windows_completed": completed,
        "windows_failed": failed,
        "windows": report_windows,
        "stability": stability,
        "failed_windows_summary": [
            {
                "name": w["name"],
                "status": w["status"],
                "error": w["error"] or "",
            }
            for w in failed_windows
        ],
        "latest_updated": False,
        "latest_update_reason": "",
        "latest_warning_reason": "",
        "latest_update_path": "",
        "latest_pointer_policy": "",
    }


def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# Walk-Forward / Regime Dataset Report")
    lines.append(f"**Run ID**: {report['run_id']}")
    lines.append(f"**Generated At**: {report['generated_at']}")
    lines.append(f"**Status**: {report['status']}")
    lines.append(f"**Suite Mode**: {report.get('suite_mode', 'FULL_SUITE')}")
    lines.append(f"**Run Mode**: {report.get('run_mode', 'FULL')}")
    lines.append(f"**Rerun Scope**: {report.get('rerun_scope', 'ALL_WINDOWS')}")
    lines.append(
        f"**Progress**: {report['windows_completed']} / {report['windows_total']} completed "
        f"(failed: {report['windows_failed']})"
    )
    lines.append("")
    if report["latest_updated"]:
        lines.append(
            f"**Latest Pointer**: updated ({report.get('latest_warning_reason', 'LATEST_UPDATED')})"
        )
    else:
        lines.append(
            f"**Latest Pointer**: not updated ({report.get('latest_warning_reason', 'UNKNOWN_REASON')})"
        )
    lines.append(
        f"**Latest Pointer Policy**: {report.get('latest_pointer_policy', '')}"
    )
    lines.append(f"**Latest Pointer Detail**: {report['latest_update_reason']}")
    lines.append("")

    lines.append("## Windows Performance")
    lines.append(
        "| Window | Start | End | Status | Gate | Decision | Sharpe | Return | MDD | Reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for window in report["windows"]:
        sharpe = f"{window['sharpe']:.3f}" if window["sharpe"] is not None else "-"
        ret = (
            f"{window['total_return']:.2%}"
            if window["total_return"] is not None
            else "-"
        )
        mdd = f"{window['mdd']:.2%}" if window["mdd"] is not None else "-"
        reason = window["error"] or "-"
        lines.append(
            f"| {window['name']} | {window['start']} | {window['end']} | {window['status']} | "
            f"{window['gate_overall']} | {window['selection_decision']} | {sharpe} | {ret} | {mdd} | {reason} |"
        )

    lines.append("")
    lines.append("## Stability Analysis (Sharpe)")
    if report["stability"]:
        lines.append("| Regime | Count | Mean | Min | Max | Median |")
        lines.append("|---|---|---|---|---|---|")
        for regime, stats in report["stability"].items():
            lines.append(
                f"| {regime} | {stats['count']} | {stats['mean_sharpe']:.3f} | "
                f"{stats['min_sharpe']:.3f} | {stats['max_sharpe']:.3f} | {stats['median_sharpe']:.3f} |"
            )
    else:
        lines.append("No stability data available.")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", default="configs/windows.json", help="Path to windows config"
    )
    parser.add_argument("--reports_dir", default="reports", help="Output directory")
    parser.add_argument(
        "--data_root",
        default="data/backtests",
        help="Unused legacy argument for compatibility",
    )
    parser.add_argument("--run_id", default="", help="Walkforward suite run id")
    parser.add_argument(
        "--suite_results_tsv", default="", help="Path to suite results TSV"
    )
    parser.add_argument(
        "--no_latest_update",
        action="store_true",
        help="Do not update walkforward_latest.* (used by rerun workflows)",
    )
    parser.add_argument(
        "--suite_mode",
        choices=["FULL_SUITE", "QUICK", "RERUN_SELECTED"],
        default="FULL_SUITE",
        help="Execution mode for pointer policy decisions",
    )
    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    config_path = Path(args.config)

    if not config_path.exists():
        print(f"Error: config {config_path} not found.")
        return 1
    with open(config_path, "r", encoding="utf-8") as handle:
        windows_config = json.load(handle)

    run_id = args.run_id.strip()
    suite_path: Optional[Path] = (
        Path(args.suite_results_tsv) if args.suite_results_tsv else None
    )

    if not run_id and suite_path:
        run_id = suite_path.parent.name
    if run_id and not suite_path:
        suite_path = reports_dir / "walkforward" / run_id / "suite_results.tsv"
    if not run_id and not suite_path:
        run_id, suite_path = detect_latest_suite_run(reports_dir)

    if not run_id or not suite_path or not suite_path.exists():
        print("Error: no suite results found. Run scripts/walkforward_suite.sh first.")
        return 1

    suite_rows = parse_suite_results(suite_path)
    run_mode = "RERUN" if args.no_latest_update else "FULL"
    rerun_scope = "FAILED_ONLY" if args.no_latest_update else "ALL_WINDOWS"
    report = build_report(
        windows_config,
        suite_rows,
        run_id,
        run_mode=run_mode,
        rerun_scope=rerun_scope,
        suite_mode=args.suite_mode,
    )
    run_dir = reports_dir / "walkforward" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    has_terminal_fail = any(
        w["status"] in {"FAILED", "ERROR"} for w in report["windows"]
    )
    run_dir_exists = run_dir.exists()
    is_latest_run = is_latest_suite_run(reports_dir, run_id)
    success_ready = (
        report["status"] == "COMPLETED"
        and report["windows_completed"] == report["windows_total"]
        and report["windows_failed"] == 0
        and not has_terminal_fail
        and run_dir_exists
        and is_latest_run
        and not args.no_latest_update
        and args.suite_mode == "FULL_SUITE"
    )

    if success_ready:
        report["latest_updated"] = True
        report["latest_warning_reason"] = "LATEST_UPDATED"
        report["latest_update_reason"] = (
            "LATEST_UPDATED policy=FULL_SUITE_COMPLETED "
            f"completed={report['windows_completed']}/{report['windows_total']}"
        )
        report["latest_update_path"] = str((reports_dir / "walkforward_latest.json"))
        report["latest_pointer_policy"] = "allow_update_full_suite_completed"
    else:
        report["latest_updated"] = False
        report["latest_update_path"] = ""
        if args.no_latest_update or args.suite_mode == "RERUN_SELECTED":
            report["latest_warning_reason"] = "RERUN_NEVER_UPDATES_LATEST_BY_POLICY"
            report["latest_update_reason"] = (
                f"RERUN_NEVER_UPDATES_LATEST_BY_POLICY run_id={run_id} "
                "walkforward_latest pointer reserved for full suite runs"
            )
            report["latest_pointer_policy"] = "block_update_rerun"
        elif args.suite_mode == "QUICK":
            report["latest_warning_reason"] = "LATEST_NOT_UPDATED_QUICK_MODE"
            report["latest_update_reason"] = (
                f"LATEST_NOT_UPDATED_QUICK_MODE suite_mode=QUICK "
                f"completed={report['windows_completed']}/{report['windows_total']}"
            )
            report["latest_pointer_policy"] = "block_update_quick"
        elif report["windows_failed"] > 0 or has_terminal_fail:
            report["latest_warning_reason"] = "LATEST_NOT_UPDATED_FAILED"
            failed_names = (
                ",".join(w["name"] for w in report["failed_windows_summary"]) or "none"
            )
            report["latest_update_reason"] = (
                f"LATEST_NOT_UPDATED_FAILED status={report['status']} "
                f"completed={report['windows_completed']}/{report['windows_total']} "
                f"failed_windows={failed_names}"
            )
            report["latest_pointer_policy"] = "block_update_failed"
        elif not is_latest_run:
            report["latest_warning_reason"] = "LATEST_NOT_UPDATED_FAILED"
            report["latest_update_reason"] = (
                f"LATEST_NOT_UPDATED_FAILED run_id={run_id} is not the latest suite run"
            )
            report["latest_pointer_policy"] = "block_update_not_latest"
        else:
            report["latest_warning_reason"] = "LATEST_NOT_UPDATED_INCOMPLETE"
            report["latest_update_reason"] = (
                f"LATEST_NOT_UPDATED_INCOMPLETE status={report['status']} "
                f"completed={report['windows_completed']}/{report['windows_total']}"
            )
            report["latest_pointer_policy"] = "block_update_incomplete"

    run_json = run_dir / "walkforward.json"
    run_md = run_dir / "walkforward.md"
    atomic_write_json(run_json, report)
    atomic_write_text(run_md, render_markdown(report))

    if report["latest_updated"]:
        atomic_write_json(reports_dir / "walkforward_latest.json", report)
        atomic_write_text(
            reports_dir / "walkforward_latest.md", render_markdown(report)
        )
        print(
            "LATEST_UPDATED "
            f"run_id={run_id} "
            f"latest_json={reports_dir / 'walkforward_latest.json'} "
            f"latest_md={reports_dir / 'walkforward_latest.md'} "
            "reason=LATEST_UPDATED"
        )
    else:
        print(
            f"WARN reason={report['latest_warning_reason']} "
            f'run_id={run_id} run_dir={run_dir} detail="{report["latest_update_reason"]}"'
        )
        rerun_latest_json = reports_dir / "walkforward_rerun_latest.json"
        if rerun_latest_json.exists():
            print(f"RERUN_LATEST_HINT path={rerun_latest_json}")

    print(f"Run reports generated in {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
