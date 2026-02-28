from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

REFRESH_HINT = "bash scripts/refresh_state.sh"
ALLOWED_STATUS = {"OK", "WARN", "FAIL", "UNKNOWN"}
DEFAULT_REPRO_THRESHOLDS = {
    "sharpe": 0.05,
    "total_return": 0.02,
    "max_drawdown": 0.02,
    "trades_count": 2.0,
}
DEFAULT_WARN_RATIO = 0.5


def _utc_now_iso(now_utc: str | None = None) -> str:
    if now_utc:
        return str(now_utc)
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_status(value: object, *, default: str = "UNKNOWN") -> str:
    status = str(value or default).strip().upper()
    return status if status in ALLOWED_STATUS else default


def _safe_rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path)


def _coerce_strings(value: object) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                out.append(text)
        return out
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return []


def _coerce_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def _load_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None, "unreadable"
    if not isinstance(obj, dict):
        return None, "invalid"
    return obj, None


def _read_file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None


def _resolve_repo_path(repo_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return (repo_root / candidate).resolve()


def _git_dir(repo_root: Path) -> Path | None:
    dot_git = repo_root / ".git"
    if dot_git.is_dir():
        return dot_git
    if dot_git.is_file():
        try:
            text = dot_git.read_text(encoding="utf-8").strip()
        except Exception:
            return None
        if text.startswith("gitdir:"):
            raw = text.split(":", 1)[1].strip()
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = (repo_root / candidate).resolve()
            return candidate
    return None


def _read_git_head_sha(repo_root: Path) -> str:
    git_dir = _git_dir(repo_root)
    if git_dir is None:
        return "UNKNOWN"
    head_path = git_dir / "HEAD"
    if not head_path.exists():
        return "UNKNOWN"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except Exception:
        return "UNKNOWN"
    if not head.startswith("ref:"):
        return head or "UNKNOWN"
    ref = head.split(":", 1)[1].strip()
    ref_path = git_dir / ref
    if ref_path.exists():
        try:
            return ref_path.read_text(encoding="utf-8").strip() or "UNKNOWN"
        except Exception:
            return "UNKNOWN"
    packed_refs = git_dir / "packed-refs"
    if packed_refs.exists():
        try:
            for line in packed_refs.read_text(encoding="utf-8").splitlines():
                row = line.strip()
                if not row or row.startswith("#") or row.startswith("^"):
                    continue
                parts = row.split()
                if len(parts) == 2 and parts[1] == ref:
                    return parts[0]
        except Exception:
            return "UNKNOWN"
    return "UNKNOWN"


def _mtime_utc(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        ts = path.stat().st_mtime
    except Exception:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _write_artifacts(
    repo_root: Path,
    output_dir: str,
    prefix: str,
    generated_utc: str,
    payload: dict[str, Any],
    markdown_lines: list[str],
) -> dict[str, str]:
    stamp = (
        generated_utc.replace("-", "")
        .replace(":", "")
        .replace("T", "_")
        .replace("Z", "")
        .replace("+00:00", "")
    )
    out_dir = (repo_root / output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{prefix}_{stamp}.json"
    md_path = out_dir / f"{prefix}_{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text("\n".join(markdown_lines).rstrip() + "\n", encoding="utf-8")
    return {
        "json": _safe_rel(repo_root, json_path),
        "markdown": _safe_rel(repo_root, md_path),
    }


def _artifact_from_daily(repo_root: Path, daily_obj: dict[str, Any] | None, key: str) -> str:
    if not isinstance(daily_obj, dict):
        return ""
    latest = daily_obj.get("latest_backtest_head")
    if not isinstance(latest, dict):
        return ""
    artifacts = latest.get("artifacts")
    if not isinstance(artifacts, dict):
        return ""
    value = artifacts.get(key)
    return str(value or "").strip()


def _extract_metrics(obj: Mapping[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(obj, Mapping):
        return None
    metrics: dict[str, float] = {}
    raw = {
        "sharpe": obj.get("sharpe"),
        "total_return": obj.get("total_return"),
        "max_drawdown": obj.get("max_drawdown"),
        "trades_count": obj.get("trades_count"),
    }
    for key, value in raw.items():
        coerced = _coerce_float(value)
        if coerced is None:
            return None
        metrics[key] = coerced
    return metrics


def _selection_context(selection_obj: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(selection_obj, Mapping):
        return {
            "regime_slice": None,
            "regime_timeframe": None,
        }
    return {
        "regime_slice": selection_obj.get("regime"),
        "regime_timeframe": selection_obj.get("regime_tf"),
        "selection_generated_utc": selection_obj.get("generated_at"),
    }


def _summary_window(summary_obj: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(summary_obj, Mapping):
        return {"start": None, "end": None}
    return {
        "start": summary_obj.get("start_ts"),
        "end": summary_obj.get("end_ts"),
    }


def _baseline_summary_path(repo_root: Path, daily_obj: dict[str, Any] | None, explicit: str) -> str:
    if explicit:
        return explicit
    return _artifact_from_daily(repo_root, daily_obj, "summary")


def _base_quant_payload(skill: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": skill,
        "status": "UNKNOWN",
        "report_only": True,
        "actions": [],
        "constraints": ["read_only", "report_only"],
        "inputs": inputs,
        "summary": "required SSOT artifacts missing or unreadable",
        "refresh_hint": REFRESH_HINT,
        "evidence_refs": [],
        "missing_artifacts": [],
        "findings": [],
    }


def _finalize_quant_payload(out: dict[str, Any]) -> dict[str, Any]:
    out["status"] = _normalize_status(out.get("status"), default="UNKNOWN")
    out["report_only"] = True
    out["actions"] = []
    out["constraints"] = ["read_only", "report_only"]
    out["refresh_hint"] = str(out.get("refresh_hint") or REFRESH_HINT)
    out["findings"] = _coerce_strings(out.get("findings"))
    out["evidence_refs"] = _coerce_strings(out.get("evidence_refs"))
    out["missing_artifacts"] = _coerce_strings(out.get("missing_artifacts"))
    if out["missing_artifacts"] and out["status"] == "OK":
        out["status"] = "WARN"
    return out


def _fingerprint_material_hash(material: dict[str, Any]) -> str:
    encoded = json.dumps(material, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def data_lineage_fingerprint(
    repo_root: Path,
    *,
    write_artifacts: bool = False,
    output_dir: str = "reports/research/lineage",
    now_utc: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    generated_utc = _utc_now_iso(now_utc)
    out = _base_quant_payload("data_lineage_fingerprint", {"source": "current_ssot"})
    out["schema_version"] = "lineage_fingerprint.v1"
    out["generated_utc"] = generated_utc

    daily_path = root / "data/state/daily_report_latest.json"
    system_path = root / "data/state/system_health_latest.json"
    freshness_path = root / "data/state/freshness_table.json"
    regime_monitor_path = root / "reports/state_atomic/regime_monitor_latest.json"

    daily_obj, daily_err = _load_json(daily_path)
    system_obj, system_err = _load_json(system_path)
    freshness_obj, freshness_err = _load_json(freshness_path)
    regime_monitor_obj, regime_monitor_err = _load_json(regime_monitor_path)

    for path, obj, err in (
        (daily_path, daily_obj, daily_err),
        (system_path, system_obj, system_err),
        (freshness_path, freshness_obj, freshness_err),
        (regime_monitor_path, regime_monitor_obj, regime_monitor_err),
    ):
        rel = _safe_rel(root, path)
        if obj is None:
            out["missing_artifacts"].append(f"{rel}:{err or 'missing'}")
        else:
            out["evidence_refs"].append(rel)

    selection_rel = _artifact_from_daily(root, daily_obj, "selection")
    summary_rel = _artifact_from_daily(root, daily_obj, "summary")
    selection_obj = None
    summary_obj = None
    if selection_rel:
        selection_abs = _resolve_repo_path(root, selection_rel)
        selection_obj, selection_err = _load_json(selection_abs)
        if selection_obj is None:
            out["missing_artifacts"].append(f"{selection_rel}:{selection_err or 'missing'}")
        else:
            out["evidence_refs"].append(_safe_rel(root, selection_abs))
    if summary_rel:
        summary_abs = _resolve_repo_path(root, summary_rel)
        summary_obj, summary_err = _load_json(summary_abs)
        if summary_obj is None:
            out["missing_artifacts"].append(f"{summary_rel}:{summary_err or 'missing'}")
        else:
            out["evidence_refs"].append(_safe_rel(root, summary_abs))

    regime_policy_source = ""
    if isinstance(regime_monitor_obj, dict):
        regime_policy_source = str(regime_monitor_obj.get("threshold_source_path") or "").strip()
    if not regime_policy_source:
        regime_policy_source = "research/policy/regime_thresholds.json"
    regime_policy_abs = _resolve_repo_path(root, regime_policy_source)
    regime_policy_obj, regime_policy_err = _load_json(regime_policy_abs)
    if regime_policy_obj is None:
        out["missing_artifacts"].append(f"{_safe_rel(root, regime_policy_abs)}:{regime_policy_err or 'missing'}")
    else:
        out["evidence_refs"].append(_safe_rel(root, regime_policy_abs))

    symbols = set()
    timeframes = set()
    if isinstance(summary_obj, Mapping):
        symbol = str(summary_obj.get("symbol") or "").strip()
        timeframe = str(summary_obj.get("timeframe") or "").strip()
        if symbol:
            symbols.add(symbol)
        if timeframe:
            timeframes.add(timeframe)
    freshness_rows = []
    if isinstance(freshness_obj, Mapping):
        rows = freshness_obj.get("rows")
        if isinstance(rows, list):
            freshness_rows = [row for row in rows if isinstance(row, dict)]
    for row in freshness_rows:
        symbol = str(row.get("symbol") or "").strip()
        timeframe = str(row.get("tf") or "").strip()
        if symbol:
            symbols.add(symbol)
        if timeframe:
            timeframes.add(timeframe)

    derived_sources: list[dict[str, Any]] = []
    derived_latest_source_mtime_utc = None
    seen_paths: set[str] = set()
    for row in freshness_rows:
        source_rel = str(row.get("source") or "").strip()
        if not source_rel or source_rel in seen_paths:
            continue
        seen_paths.add(source_rel)
        source_abs = _resolve_repo_path(root, source_rel)
        mtime_utc = _mtime_utc(source_abs)
        if mtime_utc and (derived_latest_source_mtime_utc is None or mtime_utc > derived_latest_source_mtime_utc):
            derived_latest_source_mtime_utc = mtime_utc
        derived_sources.append(
            {
                "path": _safe_rel(root, source_abs),
                "exists": source_abs.exists(),
                "source_mtime_utc": mtime_utc,
            }
        )
        if source_abs.exists():
            out["evidence_refs"].append(_safe_rel(root, source_abs))
        else:
            out["missing_artifacts"].append(f"{_safe_rel(root, source_abs)}:missing")
    derived_sources.sort(key=lambda item: str(item.get("path", "")))

    daily_sources: dict[str, Any] = {
        "daily_report_latest": {
            "path": "data/state/daily_report_latest.json",
            "exists": daily_obj is not None,
            "ts_utc": daily_obj.get("generated_utc") if isinstance(daily_obj, dict) else None,
        }
    }
    if isinstance(daily_obj, dict):
        source_map = daily_obj.get("sources")
        if isinstance(source_map, Mapping):
            for key in sorted(source_map):
                value = source_map.get(key)
                if not isinstance(value, Mapping):
                    continue
                daily_sources[str(key)] = {
                    "path": value.get("path"),
                    "exists": bool(value.get("exists", False)),
                    "ts_utc": value.get("ts_utc"),
                }

    selection_ctx = _selection_context(selection_obj)
    window_utc = _summary_window(summary_obj)
    code_ref = _read_git_head_sha(root)
    policy_hash = None
    if isinstance(regime_monitor_obj, Mapping):
        policy_hash = str(regime_monitor_obj.get("threshold_policy_sha") or "").strip() or None
    if not policy_hash:
        policy_hash = _read_file_sha256(regime_policy_abs)

    policy_version = None
    if isinstance(regime_monitor_obj, Mapping):
        policy_version = str(regime_monitor_obj.get("threshold_policy_version") or "").strip() or None
    if not policy_version and isinstance(regime_policy_obj, Mapping):
        policy_version = str(regime_policy_obj.get("name") or "").strip() or None

    fingerprint_material = {
        "code_ref": code_ref,
        "regime_slice": selection_ctx.get("regime_slice"),
        "regime_timeframe": selection_ctx.get("regime_timeframe"),
        "regime_window_utc": window_utc,
        "regime_timeline_policy": {
            "path": _safe_rel(root, regime_policy_abs),
            "version": policy_version,
            "sha256": policy_hash,
            "last_calibrated_utc": (
                regime_monitor_obj.get("last_calibrated_utc")
                if isinstance(regime_monitor_obj, Mapping)
                else None
            ),
        },
        "symbols": sorted(symbols),
        "timeframes": sorted(timeframes),
        "derived_latest_source_mtime_utc": derived_latest_source_mtime_utc,
        "freshness_table_ts_utc": (
            freshness_obj.get("generated_utc") if isinstance(freshness_obj, Mapping) else None
        ),
        "ssot_source_ts_utc": {
            key: value.get("ts_utc")
            for key, value in sorted(daily_sources.items())
            if isinstance(value, Mapping)
        },
    }

    out["code_ref"] = code_ref
    out["fingerprint_sha256"] = _fingerprint_material_hash(fingerprint_material)
    out["fingerprint_material"] = fingerprint_material
    out["daily_ssot_sources"] = daily_sources
    out["derived_data"] = {
        "freshness_table_ts_utc": fingerprint_material.get("freshness_table_ts_utc"),
        "latest_source_mtime_utc": derived_latest_source_mtime_utc,
        "sources": derived_sources,
    }
    out["findings"].extend(
        [
            f"fingerprint_sha256={out['fingerprint_sha256']}",
            f"symbols={','.join(sorted(symbols)) or 'UNKNOWN'}",
            f"timeframes={','.join(sorted(timeframes)) or 'UNKNOWN'}",
        ]
    )

    if daily_obj is None and not out["evidence_refs"]:
        out["status"] = "UNKNOWN"
        out["summary"] = "daily SSOT missing; unable to build lineage fingerprint"
    elif daily_obj is None:
        out["status"] = "WARN"
        out["summary"] = "daily SSOT missing; built partial lineage fingerprint from fallback artifacts"
    elif out["missing_artifacts"]:
        out["status"] = "WARN"
        out["summary"] = "lineage fingerprint built with partial fallback data"
    else:
        out["status"] = "OK"
        out["summary"] = "lineage fingerprint built from daily SSOT and regime policy"

    if write_artifacts:
        markdown_lines = [
            "# Data Lineage Fingerprint",
            "",
            f"- generated_utc: {generated_utc}",
            f"- fingerprint_sha256: {out['fingerprint_sha256']}",
            f"- code_ref: {code_ref}",
            f"- regime_slice: {selection_ctx.get('regime_slice') or 'UNKNOWN'}",
            f"- regime_window_utc: {window_utc.get('start') or 'UNKNOWN'} -> {window_utc.get('end') or 'UNKNOWN'}",
            f"- symbols: {', '.join(sorted(symbols)) or 'UNKNOWN'}",
            f"- timeframes: {', '.join(sorted(timeframes)) or 'UNKNOWN'}",
            f"- status: {out['status']}",
        ]
        out["artifacts"] = _write_artifacts(root, output_dir, "lineage", generated_utc, out, markdown_lines)

    return _finalize_quant_payload(out)


def _metric_drift_stats(
    baseline: dict[str, float],
    run_metrics: list[dict[str, float]],
    thresholds: Mapping[str, float],
) -> dict[str, dict[str, Any]]:
    stats: dict[str, dict[str, Any]] = {}
    for key, baseline_value in baseline.items():
        values = [row[key] for row in run_metrics if key in row]
        diffs = [abs(value - baseline_value) for value in values]
        stats[key] = {
            "baseline": baseline_value,
            "values": values,
            "max_abs_diff": max(diffs) if diffs else None,
            "mean_abs_diff": (sum(diffs) / len(diffs)) if diffs else None,
            "threshold": float(thresholds.get(key, DEFAULT_REPRO_THRESHOLDS[key])),
        }
    return stats


def _classify_repro_status(
    diff_stats: Mapping[str, Mapping[str, Any]],
    *,
    runner_available: bool,
    had_run_errors: bool,
    warn_ratio: float,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    status = "OK"
    for key in ("sharpe", "total_return", "max_drawdown", "trades_count"):
        item = diff_stats.get(key) or {}
        max_diff = _coerce_float(item.get("max_abs_diff"))
        threshold = _coerce_float(item.get("threshold"))
        if max_diff is None or threshold is None:
            continue
        if max_diff > threshold:
            status = "FAIL"
            reasons.append(f"{key}:max_abs_diff={max_diff:.6f}>threshold={threshold:.6f}")
        elif status != "FAIL" and max_diff > (threshold * warn_ratio):
            status = "WARN"
            reasons.append(f"{key}:max_abs_diff={max_diff:.6f}>warn={threshold * warn_ratio:.6f}")
    if not runner_available and status == "OK":
        status = "WARN"
        reasons.insert(0, "live backtest runner unavailable; artifact replay only")
    if had_run_errors and status == "OK":
        status = "WARN"
        reasons.append("one or more runs were degraded")
    if not reasons:
        reasons.append("all metrics within configured drift thresholds")
    return status, reasons


def backtest_repro_gate(
    repo_root: Path,
    *,
    candidate_id: str = "",
    slice_ref: str = "",
    code_ref: str = "",
    runs: int = 3,
    summary_path: str = "",
    thresholds: Mapping[str, float] | None = None,
    runner: Callable[[dict[str, Any]], Mapping[str, Any]] | None = None,
    write_artifacts: bool = False,
    output_dir: str = "reports/research/repro_gate",
    now_utc: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    generated_utc = _utc_now_iso(now_utc)
    effective_runs = max(1, int(runs))
    thresholds_map = dict(DEFAULT_REPRO_THRESHOLDS)
    if thresholds:
        for key, value in thresholds.items():
            if key in thresholds_map:
                thresholds_map[key] = float(value)

    out = _base_quant_payload(
        "backtest_repro_gate",
        {
            "candidate_id": candidate_id,
            "slice_ref": slice_ref,
            "code_ref": code_ref,
            "runs": effective_runs,
            "summary_path": summary_path,
        },
    )
    out["schema_version"] = "backtest_repro_gate.v1"
    out["generated_utc"] = generated_utc

    daily_obj, _ = _load_json(root / "data/state/daily_report_latest.json")
    baseline_summary_rel = _baseline_summary_path(root, daily_obj, summary_path)
    baseline_summary_abs = _resolve_repo_path(root, baseline_summary_rel) if baseline_summary_rel else None
    baseline_obj = None
    baseline_err = None
    if baseline_summary_abs is not None:
        baseline_obj, baseline_err = _load_json(baseline_summary_abs)
        if baseline_obj is None:
            out["missing_artifacts"].append(f"{_safe_rel(root, baseline_summary_abs)}:{baseline_err or 'missing'}")
        else:
            out["evidence_refs"].append(_safe_rel(root, baseline_summary_abs))
    else:
        out["missing_artifacts"].append("baseline_summary:missing")

    selection_obj = None
    selection_rel = _artifact_from_daily(root, daily_obj, "selection")
    if selection_rel:
        selection_abs = _resolve_repo_path(root, selection_rel)
        selection_obj, selection_err = _load_json(selection_abs)
        if selection_obj is None:
            out["missing_artifacts"].append(f"{selection_rel}:{selection_err or 'missing'}")
        else:
            out["evidence_refs"].append(_safe_rel(root, selection_abs))

    baseline_metrics = _extract_metrics(baseline_obj) if isinstance(baseline_obj, Mapping) else None
    current_code_ref = _read_git_head_sha(root)
    effective_code_ref = str(code_ref or current_code_ref or "UNKNOWN")
    baseline_candidate = str(candidate_id or "")
    if not baseline_candidate and isinstance(baseline_obj, Mapping):
        baseline_candidate = str(baseline_obj.get("candidate_id") or baseline_obj.get("strategy_id") or "").strip()
    if not slice_ref:
        selection_ctx = _selection_context(selection_obj)
        regime = str(selection_ctx.get("regime_slice") or "").strip()
        regime_tf = str(selection_ctx.get("regime_timeframe") or "").strip()
        slice_ref = "@".join(part for part in (regime, regime_tf) if part)

    run_rows: list[dict[str, Any]] = []
    successful_metrics: list[dict[str, float]] = []
    runner_available = runner is not None
    had_run_errors = False

    if baseline_metrics is None:
        out["status"] = "WARN"
        out["summary"] = "baseline summary missing or unreadable; repro gate degraded"
    else:
        for run_index in range(1, effective_runs + 1):
            if runner is None:
                run_metrics = dict(baseline_metrics)
                run_rows.append(
                    {
                        "run_index": run_index,
                        "status": "WARN",
                        "mode": "artifact_replay",
                        "metrics": run_metrics,
                        "notes": ["live backtest runner unavailable; replayed baseline summary snapshot"],
                    }
                )
                successful_metrics.append(run_metrics)
                continue
            try:
                raw_result = runner(
                    {
                        "candidate_id": baseline_candidate,
                        "slice_ref": slice_ref,
                        "code_ref": effective_code_ref,
                        "run_index": run_index,
                        "summary_path": baseline_summary_rel,
                    }
                )
            except Exception as exc:
                had_run_errors = True
                run_rows.append(
                    {
                        "run_index": run_index,
                        "status": "WARN",
                        "mode": "live_runner",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            run_metrics = _extract_metrics(raw_result)
            if run_metrics is None:
                had_run_errors = True
                run_rows.append(
                    {
                        "run_index": run_index,
                        "status": "WARN",
                        "mode": "live_runner",
                        "error": "runner output missing required metrics",
                    }
                )
                continue
            successful_metrics.append(run_metrics)
            run_rows.append(
                {
                    "run_index": run_index,
                    "status": "OK",
                    "mode": "live_runner",
                    "metrics": run_metrics,
                }
            )

    out["execution_mode"] = "live_runner" if runner_available else "artifact_replay"
    out["runner_available"] = runner_available
    out["baseline"] = {
        "summary_path": baseline_summary_rel or None,
        "candidate_id": baseline_candidate or None,
        "slice_ref": slice_ref or None,
        "code_ref": effective_code_ref,
        "current_code_ref": current_code_ref,
        "code_ref_match": None if not code_ref else (code_ref == current_code_ref),
        "metrics": baseline_metrics,
    }
    out["runs"] = run_rows
    out["thresholds"] = thresholds_map

    if baseline_metrics is None or not successful_metrics:
        if baseline_metrics is None:
            out["classification"] = {
                "status": "WARN",
                "reasons": ["baseline summary missing or unreadable"],
            }
        else:
            out["classification"] = {
                "status": "WARN",
                "reasons": ["no successful runs available for drift comparison"],
            }
        out["diff_stats"] = {}
        if baseline_metrics is None:
            out["findings"].append("baseline_metrics=UNAVAILABLE")
    else:
        diff_stats = _metric_drift_stats(baseline_metrics, successful_metrics, thresholds_map)
        status, reasons = _classify_repro_status(
            diff_stats,
            runner_available=runner_available,
            had_run_errors=had_run_errors,
            warn_ratio=DEFAULT_WARN_RATIO,
        )
        out["status"] = status
        out["summary"] = (
            "repro gate completed from live runner"
            if runner_available
            else "repro gate completed in artifact replay mode"
        )
        out["classification"] = {"status": status, "reasons": reasons}
        out["diff_stats"] = diff_stats
        out["findings"].extend(
            [
                f"candidate_id={baseline_candidate or 'UNKNOWN'}",
                f"slice_ref={slice_ref or 'UNKNOWN'}",
                f"execution_mode={out['execution_mode']}",
            ]
        )
        for key in ("sharpe", "total_return", "max_drawdown", "trades_count"):
            item = diff_stats.get(key) or {}
            max_diff = item.get("max_abs_diff")
            if max_diff is not None:
                out["findings"].append(f"{key}_max_abs_diff={float(max_diff):.6f}")

    if baseline_candidate and isinstance(baseline_obj, Mapping):
        baseline_from_summary = str(
            baseline_obj.get("candidate_id") or baseline_obj.get("strategy_id") or ""
        ).strip()
        if candidate_id and baseline_from_summary and candidate_id != baseline_from_summary:
            out["status"] = "WARN" if out.get("status") == "OK" else out.get("status", "WARN")
            out["classification"] = out.get("classification", {"status": "WARN", "reasons": []})
            reasons = out["classification"].setdefault("reasons", [])
            if isinstance(reasons, list):
                reasons.append(
                    f"candidate_id mismatch requested:{candidate_id} baseline:{baseline_from_summary}"
                )

    if out["status"] == "UNKNOWN":
        out["status"] = "WARN"
        out["summary"] = "repro gate degraded; no live runner available"

    if write_artifacts:
        markdown_lines = [
            "# Backtest Repro Gate",
            "",
            f"- generated_utc: {generated_utc}",
            f"- status: {out['status']}",
            f"- execution_mode: {out.get('execution_mode')}",
            f"- candidate_id: {baseline_candidate or 'UNKNOWN'}",
            f"- slice_ref: {slice_ref or 'UNKNOWN'}",
            f"- code_ref: {effective_code_ref}",
            f"- runs: {effective_runs}",
        ]
        classification = out.get("classification") or {}
        reasons = classification.get("reasons") if isinstance(classification, Mapping) else []
        if isinstance(reasons, list):
            for reason in reasons[:6]:
                markdown_lines.append(f"- reason: {reason}")
        out["artifacts"] = _write_artifacts(root, output_dir, "repro", generated_utc, out, markdown_lines)

    return _finalize_quant_payload(out)
