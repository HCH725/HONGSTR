#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


JOB_LABEL = "obsidian_dashboards_export"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_info(message: str) -> None:
    print(f"INFO {JOB_LABEL}: {message} ts_utc={now_utc_iso()}")


def log_warn(message: str) -> None:
    print(f"WARN {JOB_LABEL}: {message} ts_utc={now_utc_iso()}", file=sys.stderr)


def read_json(path: Path) -> Any:
    if not path.exists():
        log_warn(f"source_missing path={path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        log_warn(f"source_invalid_json path={path} err={exc}")
        return None


def safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def safe_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def pick(d: dict[str, Any], keys: Iterable[str], default: str = "-") -> str:
    for key in keys:
        value = d.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return default


def ensure_bullets(items: list[str], minimum: int = 3, maximum: int = 7) -> list[str]:
    filtered = [item.strip() for item in items if item and item.strip()]
    if len(filtered) < minimum:
        while len(filtered) < minimum:
            filtered.append("Data is partial. Refer to source paths for details.")
    return filtered[:maximum]


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        rows = [["-", "-", "-"][: len(headers)]]
    header_line = "| " + " | ".join(headers) + " |"
    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    row_lines = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header_line, sep_line] + row_lines)


def render_page(
    title: str,
    generated_utc: str,
    source_paths: list[str],
    bullets: list[str],
    table_headers: list[str],
    table_rows: list[list[str]],
) -> str:
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- generated_utc: `{generated_utc}`")
    lines.append("- source_paths:")
    for path in source_paths:
        lines.append(f"  - `{path}`")
    lines.append("")
    lines.append("## Summary")
    for bullet in ensure_bullets(bullets):
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("## Key Table")
    lines.append(render_table(table_headers, table_rows))
    lines.append("")
    return "\n".join(lines)


def healthpack_page(state_dir: Path, generated_utc: str) -> str:
    system_rel = "data/state/system_health_latest.json"
    catalog_rel = "data/state/data_catalog_latest.json"
    changes_rel = "data/state/changes_latest.json"
    system_path = state_dir / "system_health_latest.json"
    catalog_path = state_dir / "data_catalog_latest.json"
    changes_path = state_dir / "changes_latest.json"
    system = safe_dict(read_json(system_path))
    catalog = safe_dict(read_json(catalog_path))
    changes = safe_dict(read_json(changes_path))

    components = safe_dict(system.get("components"))
    component_rows: list[list[str]] = []
    for name in sorted(components.keys()):
        row = safe_dict(components.get(name))
        status = pick(row, ["status", "overall", "result"], "UNKNOWN")
        detail = pick(row, ["top_reason", "reason", "note", "message"], "-")
        component_rows.append([name, status, detail])
    component_rows = component_rows[:10]

    datasets = safe_list(catalog.get("datasets"))
    bullets = [
        f"System health status is `{pick(system, ['ssot_status', 'status'], 'UNKNOWN')}`.",
        f"Tracked health components: `{len(component_rows)}`.",
        f"Catalog datasets discovered: `{len(datasets)}`.",
        f"Change log entries available: `{len(safe_list(changes.get('changes')) or safe_list(changes.get('rows')) )}`.",
    ]

    return render_page(
        title="10-HealthPack",
        generated_utc=generated_utc,
        source_paths=[system_rel, catalog_rel, changes_rel],
        bullets=bullets,
        table_headers=["component", "status", "detail"],
        table_rows=component_rows,
    )


def freshness_page(state_dir: Path, generated_utc: str) -> str:
    freshness_rel = "data/state/freshness_table.json"
    freshness_path = state_dir / "freshness_table.json"
    freshness = safe_dict(read_json(freshness_path))
    rows = safe_list(freshness.get("rows"))

    counters: dict[str, int] = {}
    table_rows: list[list[str]] = []
    default_profile = pick(freshness, ["default_profile"], "-")
    for row_any in rows[:12]:
        row = safe_dict(row_any)
        status = pick(row, ["status"], "UNKNOWN").upper()
        counters[status] = counters.get(status, 0) + 1
        table_rows.append(
            [
                pick(row, ["symbol", "dataset", "id"], "-"),
                pick(row, ["tf", "timeframe", "interval"], "-"),
                pick(row, ["profile"], default_profile),
                status,
                pick(row, ["lag_sec", "age_sec", "lag_seconds"], "-"),
            ]
        )

    bullets = [
        f"Freshness rows exported: `{len(rows)}`.",
        f"Default profile: `{default_profile}`.",
        f"Status distribution (sampled): `{counters or {'UNKNOWN': 0}}`.",
        f"Freshness timestamp: `{pick(freshness, ['ts_utc', 'generated_utc'], '-')}`.",
    ]

    return render_page(
        title="20-Freshness",
        generated_utc=generated_utc,
        source_paths=[freshness_rel],
        bullets=bullets,
        table_headers=["symbol_or_dataset", "tf", "profile", "status", "lag_sec"],
        table_rows=table_rows,
    )


def coverage_page(state_dir: Path, generated_utc: str) -> str:
    coverage_rel = "data/state/coverage_matrix_latest.json"
    coverage_path = state_dir / "coverage_matrix_latest.json"
    coverage = safe_dict(read_json(coverage_path))
    rows = safe_list(coverage.get("rows"))
    totals = safe_dict(coverage.get("totals"))

    status_counts: dict[str, int] = {}
    for row_any in rows:
        row = safe_dict(row_any)
        status = pick(row, ["status"], "UNKNOWN").upper()
        status_counts[status] = status_counts.get(status, 0) + 1

    table_rows = [
        ["done", str(totals.get("done", "-"))],
        ["in_progress", str(totals.get("inProgress", totals.get("in_progress", "-")))],
        ["blocked", str(totals.get("blocked", "-"))],
        ["needs_rebase", str(totals.get("needs_rebase", "-"))],
        ["rows", str(len(rows))],
    ]

    bullets = [
        f"Coverage matrix rows: `{len(rows)}`.",
        f"Coverage totals snapshot: `{totals or {}}`.",
        f"Coverage status counts: `{status_counts or {'UNKNOWN': 0}}`.",
        f"Coverage timestamp: `{pick(coverage, ['ts_utc', 'generated_utc'], '-')}`.",
    ]

    return render_page(
        title="30-Coverage",
        generated_utc=generated_utc,
        source_paths=[coverage_rel],
        bullets=bullets,
        table_headers=["metric", "value"],
        table_rows=table_rows,
    )


def brakes_page(state_dir: Path, generated_utc: str) -> str:
    brakes_rel = "data/state/brake_health_latest.json"
    brakes_path = state_dir / "brake_health_latest.json"
    brakes = safe_dict(read_json(brakes_path))
    results = safe_list(brakes.get("results"))

    table_rows: list[list[str]] = []
    for result_any in results[:12]:
        result = safe_dict(result_any)
        table_rows.append(
            [
                pick(result, ["name", "check", "id"], "-"),
                pick(result, ["status", "result"], "UNKNOWN"),
                pick(result, ["reason", "note", "message"], "-"),
            ]
        )

    bullets = [
        f"Brake overall fail flag: `{brakes.get('overall_fail', '-')}`.",
        f"Brake status: `{pick(brakes, ['status'], 'UNKNOWN')}`.",
        f"Brake checks listed: `{len(results)}`.",
        f"Brake timestamp: `{pick(brakes, ['ts_utc', 'timestamp', 'updated_at_utc'], '-')}`.",
    ]

    return render_page(
        title="40-Brakes",
        generated_utc=generated_utc,
        source_paths=[brakes_rel],
        bullets=bullets,
        table_headers=["check", "status", "detail"],
        table_rows=table_rows,
    )


def regime_page(state_dir: Path, generated_utc: str) -> str:
    regime_rel = "data/state/regime_monitor_latest.json"
    regime_path = state_dir / "regime_monitor_latest.json"
    regime = safe_dict(read_json(regime_path))
    reason = regime.get("reason")
    if isinstance(reason, list):
        reason_text = "; ".join(str(item) for item in reason[:3]) or "-"
    else:
        reason_text = str(reason) if reason is not None else "-"

    table_rows = [
        ["overall", pick(regime, ["overall"], "UNKNOWN")],
        ["threshold_metric", pick(regime, ["threshold_metric"], "-")],
        ["threshold_value", pick(regime, ["threshold_value"], "-")],
        ["observed_value", pick(regime, ["threshold_observed_value"], "-")],
        ["suggestion", pick(regime, ["suggestion"], "-")],
    ]

    bullets = [
        f"Regime overall state: `{pick(regime, ['overall'], 'UNKNOWN')}`.",
        f"Primary reason: `{reason_text}`.",
        f"Calibration status: `{pick(regime, ['calibration_status'], '-')}`.",
        f"Monitor timestamp: `{pick(regime, ['ts_utc', 'updated_at_utc'], '-')}`.",
    ]

    return render_page(
        title="50-Regime",
        generated_utc=generated_utc,
        source_paths=[regime_rel],
        bullets=bullets,
        table_headers=["field", "value"],
        table_rows=table_rows,
    )


def resolve_primary_vault(primary_root: Path) -> Path:
    if primary_root.name == "HONGSTR":
        return primary_root
    return primary_root / "HONGSTR"


def export_dashboards(repo_root: Path, generated_utc: str | None = None) -> dict[str, Any]:
    if generated_utc is None:
        generated_utc = now_utc_iso()

    state_dir = repo_root / "data" / "state"
    primary_root = Path(
        os.environ.get("OBSIDIAN_PRIMARY_ROOT", str(repo_root / "_local" / "obsidian_vault"))
    )
    vault_root = resolve_primary_vault(primary_root)
    output_dir = vault_root / "Dashboards"
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = {
        "10-HealthPack.md": healthpack_page(state_dir, generated_utc),
        "20-Freshness.md": freshness_page(state_dir, generated_utc),
        "30-Coverage.md": coverage_page(state_dir, generated_utc),
        "40-Brakes.md": brakes_page(state_dir, generated_utc),
        "50-Regime.md": regime_page(state_dir, generated_utc),
    }

    for filename, content in pages.items():
        (output_dir / filename).write_text(content, encoding="utf-8")

    return {
        "generated_utc": generated_utc,
        "output_dir": str(output_dir),
        "files_written": sorted(pages.keys()),
    }


def main() -> int:
    enabled = os.environ.get("DASHBOARDS_EXPORT_ENABLED", "1")
    if enabled != "1":
        log_info(f"disabled DASHBOARDS_EXPORT_ENABLED={enabled}")
        return 0

    repo_root = Path(
        os.environ.get("HONGSTR_REPO_ROOT", str(Path(__file__).resolve().parents[1]))
    )
    try:
        result = export_dashboards(repo_root=repo_root)
        log_info(
            f"done output_dir={result['output_dir']} files_written={','.join(result['files_written'])}"
        )
        return 0
    except Exception as exc:
        log_warn(f"export_failed err={exc}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
