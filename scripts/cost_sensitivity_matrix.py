#!/usr/bin/env python3
"""
Report-only cost sensitivity matrix derived from existing backtest artifacts.

This script does not recompute backtests and does not write canonical data/state files.
`scripts/state_snapshots.py` remains the sole writer for `data/state/*`.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from _ssot_meta import _get_producer_git_sha
    from backtest_runs_index import discover_backtest_candidates
    from discovery_utils import iter_nested_mappings, read_json_file, repo_relative_path, to_utc_iso
except ImportError:  # pragma: no cover - package import fallback
    from scripts._ssot_meta import _get_producer_git_sha
    from scripts.backtest_runs_index import discover_backtest_candidates
    from scripts.discovery_utils import iter_nested_mappings, read_json_file, repo_relative_path, to_utc_iso

SCHEMA_VERSION = "cost_sensitivity_matrix.v1"
SHARPE_DROP_50_OK_THRESHOLD = 0.20
MDD_WORSEN_50_OK_THRESHOLD = 0.02
WARN_THRESHOLD_MULTIPLIER = 2.0
SCENARIO_CONTAINER_KEYS = ("scenarios", "cost_scenarios", "fees", "slippage", "scenario_metrics")
TARGET_SCENARIOS = {
    "cost_x1_2": 1.2,
    "cost_x1_5": 1.5,
}
BASELINE_ALIASES = ("baseline", "base")
FACTOR_FIELD_NAMES = (
    "factor",
    "multiplier",
    "cost_multiplier",
    "fee_multiplier",
    "slippage_multiplier",
    "cost_x",
    "x",
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _first_numeric(node: Any, keys: tuple[str, ...], coerce) -> Any | None:
    for mapping in iter_nested_mappings(node, max_depth=2):
        for key in keys:
            if key not in mapping:
                continue
            parsed = coerce(mapping.get(key))
            if parsed is not None:
                return parsed
    return None


def _extract_metrics(node: Any) -> dict[str, Any]:
    return {
        "sharpe": _first_numeric(node, ("sharpe",), _as_float),
        "mdd": _first_numeric(node, ("mdd", "max_drawdown", "max_mdd"), _as_float),
        "ret": _first_numeric(node, ("ret", "return", "total_return", "portfolio_return"), _as_float),
        "trades": _first_numeric(
            node,
            ("trades", "trades_count", "trade_count", "portfolio_trades"),
            _as_int,
        ),
    }


def _metrics_completeness(metrics: dict[str, Any]) -> int:
    return sum(1 for key in ("sharpe", "mdd", "ret", "trades") if metrics.get(key) is not None)


def _merge_metrics(*nodes: Any) -> dict[str, Any]:
    merged = {"sharpe": None, "mdd": None, "ret": None, "trades": None}
    for node in nodes:
        extracted = _extract_metrics(node)
        for key, value in extracted.items():
            if merged.get(key) is None and value is not None:
                merged[key] = value
    return merged


def _baseline_cost_reference(summary_payload: Any) -> dict[str, float]:
    if not isinstance(summary_payload, dict):
        return {}
    config = summary_payload.get("config")
    if not isinstance(config, dict):
        return {}
    refs: dict[str, float] = {}
    for key in ("fee_bps", "slippage_bps"):
        value = _as_float(config.get(key))
        if value is not None and value > 0:
            refs[key] = value
    return refs


def _scenario_key_from_factor(value: float | None) -> str | None:
    if value is None:
        return None
    if abs(value - 1.0) <= 0.051:
        return "baseline"
    for key, target in TARGET_SCENARIOS.items():
        if abs(value - target) <= 0.051:
            return key
    return None


def _normalize_hint(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _scenario_key_from_hint(value: Any) -> str | None:
    norm = _normalize_hint(value)
    if not norm:
        return None
    if re.search(r"(^|_)(cost_)?x?1_5(x)?($|_)", norm):
        return "cost_x1_5"
    if re.search(r"(^|_)(cost_)?x?1_2(x)?($|_)", norm):
        return "cost_x1_2"
    if re.search(r"(^|_)(50pct|50_percent|pct50|plus50|plus_50|fee_50|slippage_50)($|_)", norm):
        return "cost_x1_5"
    if re.search(r"(^|_)(20pct|20_percent|pct20|plus20|plus_20|fee_20|slippage_20)($|_)", norm):
        return "cost_x1_2"
    if any(re.search(rf"(^|_){alias}($|_)", norm) for alias in BASELINE_ALIASES):
        return "baseline"
    return None


def _scenario_key_from_cost_fields(entry: dict[str, Any], baseline_costs: dict[str, float]) -> str | None:
    ratios: list[float] = []
    for key in ("fee_bps", "slippage_bps"):
        baseline_value = baseline_costs.get(key)
        candidate_value = _as_float(entry.get(key))
        if baseline_value is None or baseline_value <= 0 or candidate_value is None:
            continue
        ratios.append(candidate_value / baseline_value)
    if not ratios:
        return None
    average_ratio = sum(ratios) / float(len(ratios))
    return _scenario_key_from_factor(average_ratio)


def _scenario_key_from_entry(key_hint: Any, entry: dict[str, Any], baseline_costs: dict[str, float]) -> str | None:
    for field_name in FACTOR_FIELD_NAMES:
        label = _scenario_key_from_factor(_as_float(entry.get(field_name)))
        if label is not None:
            return label

    for candidate in (
        key_hint,
        entry.get("key"),
        entry.get("id"),
        entry.get("label"),
        entry.get("name"),
        entry.get("scenario"),
        entry.get("variant"),
    ):
        label = _scenario_key_from_hint(candidate)
        if label is not None:
            return label

    return _scenario_key_from_cost_fields(entry, baseline_costs)


def _parse_scenario_container(
    container: Any,
    *,
    container_hint: str,
    baseline_costs: dict[str, float],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []

    if isinstance(container, dict):
        for key, value in container.items():
            if not isinstance(value, dict):
                continue
            label = _scenario_key_from_entry(key, value, baseline_costs)
            if label is None:
                continue
            metrics = _extract_metrics(value)
            entries.append(
                {
                    "label": label,
                    "metrics": metrics,
                    "completeness": _metrics_completeness(metrics),
                    "container_hint": container_hint,
                }
            )
        if entries:
            return entries

        label = _scenario_key_from_entry(container_hint, container, baseline_costs)
        if label is not None:
            metrics = _extract_metrics(container)
            entries.append(
                {
                    "label": label,
                    "metrics": metrics,
                    "completeness": _metrics_completeness(metrics),
                    "container_hint": container_hint,
                }
            )
        return entries

    if isinstance(container, list):
        for item in container:
            if not isinstance(item, dict):
                continue
            label = _scenario_key_from_entry(container_hint, item, baseline_costs)
            if label is None:
                continue
            metrics = _extract_metrics(item)
            entries.append(
                {
                    "label": label,
                    "metrics": metrics,
                    "completeness": _metrics_completeness(metrics),
                    "container_hint": container_hint,
                }
            )
    return entries


def _collect_scenario_entries(payload: Any, baseline_costs: dict[str, float]) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []

    entries: list[dict[str, Any]] = []
    for mapping in iter_nested_mappings(payload, max_depth=4):
        for key in SCENARIO_CONTAINER_KEYS:
            container = mapping.get(key)
            if not isinstance(container, (dict, list)):
                continue
            entries.extend(
                _parse_scenario_container(
                    container,
                    container_hint=key,
                    baseline_costs=baseline_costs,
                )
            )
    return entries


def _best_entry(entries: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    selected: dict[str, Any] | None = None
    for entry in entries:
        if entry.get("label") != label:
            continue
        if selected is None:
            selected = entry
            continue
        current_score = int(entry.get("completeness", 0) or 0)
        selected_score = int(selected.get("completeness", 0) or 0)
        if current_score > selected_score:
            selected = entry
    return selected


def _delta_numeric(baseline: float | int | None, scenario: float | int | None, *, mdd: bool = False) -> float | int | None:
    if baseline is None or scenario is None:
        return None
    if mdd:
        return float(abs(float(scenario)) - abs(float(baseline)))
    return float(baseline) - float(scenario)


def _classify_row(deltas: dict[str, Any]) -> str:
    checks: list[tuple[float, float]] = []
    sharpe_drop = _as_float(deltas.get("sharpe_drop_50"))
    if sharpe_drop is not None:
        checks.append((max(0.0, sharpe_drop), SHARPE_DROP_50_OK_THRESHOLD))

    mdd_worsen = _as_float(deltas.get("mdd_worsen_50"))
    if mdd_worsen is not None:
        checks.append((max(0.0, mdd_worsen), MDD_WORSEN_50_OK_THRESHOLD))

    if not checks:
        return "UNKNOWN"

    worst_ratio = max((value / threshold) if threshold > 0 else 0.0 for value, threshold in checks)
    if worst_ratio <= 1.0:
        return "OK"
    if worst_ratio <= WARN_THRESHOLD_MULTIPLIER:
        return "WARN"
    return "FAIL"


def _timestamp_from_payloads(*payloads: Any) -> str | None:
    candidates = (
        "ts_utc",
        "generated_utc",
        "timestamp_utc",
        "timestamp",
        "generated_at",
        "updated_at_utc",
    )
    for payload in payloads:
        if not isinstance(payload, dict):
            continue
        for key in candidates:
            if key not in payload:
                continue
            ts_utc = to_utc_iso(payload.get(key))
            if ts_utc:
                return ts_utc
    return None


def _artifact_payloads_for_candidate(
    candidate: dict[str, Any],
    repo_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    payloads: dict[str, dict[str, Any]] = {
        "summary": {},
        "gate": {},
        "leaderboard": {},
    }
    read_inputs: list[str] = []

    for key in ("summary", "gate", "leaderboard"):
        path = candidate.get(f"{key}_path")
        if not isinstance(path, Path):
            continue
        if not path.exists():
            continue
        payload = read_json_file(path)
        if isinstance(payload, dict):
            payloads[key] = payload
            read_inputs.append(repo_relative_path(path, repo_root))

    return payloads["summary"], payloads["gate"], payloads["leaderboard"], read_inputs


def _build_row(candidate: dict[str, Any], repo_root: Path) -> tuple[dict[str, Any], list[str]]:
    summary_payload, gate_payload, leaderboard_payload, read_inputs = _artifact_payloads_for_candidate(candidate, repo_root)
    baseline_metrics = _merge_metrics(summary_payload, gate_payload, leaderboard_payload)
    baseline_costs = _baseline_cost_reference(summary_payload)

    scenario_entries: list[dict[str, Any]] = []
    for payload in (summary_payload, gate_payload, leaderboard_payload):
        scenario_entries.extend(_collect_scenario_entries(payload, baseline_costs))

    baseline_entry = _best_entry(scenario_entries, "baseline")
    if _metrics_completeness(baseline_metrics) == 0 and baseline_entry is not None:
        baseline_metrics = dict(baseline_entry["metrics"])

    target_entries = {key: _best_entry(scenario_entries, key) for key in TARGET_SCENARIOS}
    target_metrics = {
        key: (dict(entry["metrics"]) if entry is not None else None)
        for key, entry in target_entries.items()
    }

    deltas = {
        "sharpe_drop_20": None,
        "sharpe_drop_50": None,
        "mdd_worsen_20": None,
        "mdd_worsen_50": None,
        "ret_drop_20": None,
        "ret_drop_50": None,
        "trades_delta_20": None,
        "trades_delta_50": None,
    }
    reasons: list[str] = []

    for label, suffix in (("cost_x1_2", "20"), ("cost_x1_5", "50")):
        metrics = target_metrics.get(label)
        if metrics is None:
            continue
        deltas[f"sharpe_drop_{suffix}"] = _delta_numeric(baseline_metrics.get("sharpe"), metrics.get("sharpe"))
        deltas[f"mdd_worsen_{suffix}"] = _delta_numeric(
            baseline_metrics.get("mdd"),
            metrics.get("mdd"),
            mdd=True,
        )
        deltas[f"ret_drop_{suffix}"] = _delta_numeric(baseline_metrics.get("ret"), metrics.get("ret"))
        deltas[f"trades_delta_{suffix}"] = _delta_numeric(
            baseline_metrics.get("trades"),
            metrics.get("trades"),
        )

    if target_metrics["cost_x1_2"] is None and target_metrics["cost_x1_5"] is None:
        reasons.append("ONLY_BASELINE_AVAILABLE")
    else:
        if target_metrics["cost_x1_2"] is None:
            reasons.append("MISSING_COST_X1_2")
        if target_metrics["cost_x1_5"] is None:
            reasons.append("MISSING_COST_X1_5")

    status = _classify_row(deltas)
    if status == "UNKNOWN" and "ONLY_BASELINE_AVAILABLE" not in reasons:
        reasons.append("INCOMPLETE_SCENARIO_METRICS")

    timestamp_utc = _timestamp_from_payloads(summary_payload, gate_payload, leaderboard_payload)
    if timestamp_utc is None:
        timestamp_utc = to_utc_iso(candidate.get("ts_utc"))

    run_dir = candidate.get("run_dir")
    run_dir_rel = repo_relative_path(run_dir, repo_root) if isinstance(run_dir, Path) else None

    row = {
        "run_id": str(candidate.get("run_id") or (run_dir.name if isinstance(run_dir, Path) else "UNKNOWN")),
        "run_dir": run_dir_rel,
        "timestamp_utc": timestamp_utc,
        "strategy": candidate.get("strategy"),
        "timeframe": candidate.get("timeframe"),
        "regime": candidate.get("regime"),
        "baseline": baseline_metrics,
        "cost_x1_2": target_metrics["cost_x1_2"],
        "cost_x1_5": target_metrics["cost_x1_5"],
        "deltas": deltas,
        "status": status,
        "reasons": reasons,
        "artifacts_read": read_inputs,
    }
    return row, read_inputs


def _build_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = {
        "OK": 0,
        "WARN": 0,
        "FAIL": 0,
        "UNKNOWN": 0,
    }
    scenario_rows = 0
    baseline_only_rows = 0

    for row in rows:
        status = str(row.get("status") or "UNKNOWN").upper()
        status_counts[status if status in status_counts else "UNKNOWN"] += 1
        reasons = row.get("reasons")
        if isinstance(reasons, list) and "ONLY_BASELINE_AVAILABLE" in reasons:
            baseline_only_rows += 1
        else:
            scenario_rows += 1

    return {
        "rows_total": len(rows),
        "scenario_rows": scenario_rows,
        "baseline_only_rows": baseline_only_rows,
        "status_counts": status_counts,
    }


def _overall_status(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "UNKNOWN"
    statuses = {str(row.get("status") or "UNKNOWN").upper() for row in rows}
    if "FAIL" in statuses:
        return "FAIL"
    if "WARN" in statuses:
        return "WARN"
    if "OK" in statuses:
        return "OK"
    if all("ONLY_BASELINE_AVAILABLE" in (row.get("reasons") or []) for row in rows):
        return "OK"
    return "UNKNOWN"


def build_cost_sensitivity_matrix_payload(
    *,
    repo_root: Path | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve() if repo_root is not None else Path(".").resolve()
    rows: list[dict[str, Any]] = []

    candidates, candidates_source, discovery_inputs = discover_backtest_candidates(root)
    source_inputs: set[str] = set(discovery_inputs)

    for candidate in candidates:
        row, read_inputs = _build_row(candidate, root)
        rows.append(row)
        source_inputs.update(read_inputs)

    rows.sort(
        key=lambda row: (
            row.get("timestamp_utc") or "",
            row.get("run_id") or "",
        ),
        reverse=True,
    )

    totals = _build_totals(rows)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "producer_git_sha": _get_producer_git_sha(),
        "generated_utc": generated_utc or _utc_now_iso(),
        "candidates_source": candidates_source,
        "overall": _overall_status(rows),
        "totals": totals,
        "source_inputs": sorted(source_inputs),
        "rows": rows,
    }
    return payload


def main() -> int:
    payload = build_cost_sensitivity_matrix_payload(repo_root=Path(".").resolve())
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
