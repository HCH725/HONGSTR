from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REFRESH_HINT = "bash scripts/refresh_state.sh"
ALLOWED_STATUS = {"OK", "WARN", "FAIL", "UNKNOWN"}


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


def _load_jsonl_first(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, "missing"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return None, "unreadable"
    for line in lines:
        row = (line or "").strip()
        if not row:
            continue
        try:
            obj = json.loads(row)
        except Exception:
            continue
        if isinstance(obj, dict):
            return obj, None
    return None, "invalid"


def _safe_rel(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path(repo_root).resolve()))
    except Exception:
        return str(path)


def _normalize_status(value: object, *, default: str = "UNKNOWN") -> str:
    s = str(value or default).strip().upper()
    return s if s in ALLOWED_STATUS else default


def _coerce_str_list(value: object) -> list[str]:
    if isinstance(value, list):
        out = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    return []


def _add_evidence(out: dict[str, Any], ref: str) -> None:
    refs = out.setdefault("evidence_refs", [])
    if not isinstance(refs, list):
        refs = []
        out["evidence_refs"] = refs
    if ref not in refs:
        refs.append(ref)


def _add_missing(out: dict[str, Any], ref: str, err: str | None) -> None:
    miss = out.setdefault("missing_artifacts", [])
    if not isinstance(miss, list):
        miss = []
        out["missing_artifacts"] = miss
    token = f"{ref}:{err or 'missing'}"
    if token not in miss:
        miss.append(token)


def _finalize(out: dict[str, Any]) -> dict[str, Any]:
    out["status"] = _normalize_status(out.get("status"), default="UNKNOWN")
    out["report_only"] = True
    out["actions"] = []
    out["constraints"] = ["read_only", "report_only"]
    out["refresh_hint"] = str(out.get("refresh_hint") or REFRESH_HINT)
    out["findings"] = _coerce_str_list(out.get("findings"))
    out["evidence_refs"] = _coerce_str_list(out.get("evidence_refs"))
    out["missing_artifacts"] = _coerce_str_list(out.get("missing_artifacts"))
    if out["missing_artifacts"] and out["status"] == "OK":
        out["status"] = "WARN"
    return out


def _base_payload(skill: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": skill,
        "status": "UNKNOWN",
        "report_only": True,
        "actions": [],
        "constraints": ["read_only", "report_only"],
        "inputs": inputs,
        "summary": "required research artifact missing or unreadable",
        "refresh_hint": REFRESH_HINT,
        "evidence_refs": [],
        "missing_artifacts": [],
        "findings": [],
    }


def backtest_reproducibility_audit(
    repo_root: Path,
    manifest_path: str = "reports/research/backtest_manifest.json",
    split_ref: str = "",
    run_id: str = "",
) -> dict[str, Any]:
    """Report-only backtest reproducibility skeleton with SSOT/read-only fallback evidence."""
    inputs = {"manifest_path": manifest_path, "split_ref": split_ref, "run_id": run_id}
    out = _base_payload("backtest_reproducibility_audit", inputs)

    root = Path(repo_root).resolve()

    manifest_abs = (root / manifest_path).resolve()
    obj, err = _load_json(manifest_abs)
    if obj is None:
        _add_missing(out, manifest_path, err)
    else:
        _add_evidence(out, _safe_rel(root, manifest_abs))
        out["status"] = "OK"
        out["summary"] = "manifest found; reproducibility fields surfaced"
        out["findings"].extend(
            [
                f"git_commit={obj.get('git_commit', 'UNKNOWN')}",
                f"created_utc={obj.get('created_utc', 'UNKNOWN')}",
                f"split_ref={obj.get('split_ref') or split_ref or 'UNKNOWN'}",
            ]
        )
        if run_id:
            out["findings"].append(f"run_id={run_id}")
        if split_ref and obj.get("split_ref") and split_ref != obj.get("split_ref"):
            out["status"] = "WARN"
            out["summary"] = "manifest found; split_ref mismatch detected"
            out["findings"].append(
                f"split_ref_mismatch=requested:{split_ref}|manifest:{obj.get('split_ref')}"
            )

    # Fallback evidence from state_atomic/SSOT (read-only)
    coverage_jsonl_rel = "reports/state_atomic/coverage_table.jsonl"
    coverage_abs = (root / coverage_jsonl_rel).resolve()
    coverage_row, cov_err = _load_jsonl_first(coverage_abs)
    if coverage_row is not None:
        _add_evidence(out, _safe_rel(root, coverage_abs) + "#first_row")
        out["findings"].append(f"coverage_status={coverage_row.get('status', 'UNKNOWN')}")
    elif cov_err not in {None, "missing"}:
        _add_missing(out, coverage_jsonl_rel, cov_err)

    health_rel = "data/state/system_health_latest.json"
    health_abs = (root / health_rel).resolve()
    health_obj, health_err = _load_json(health_abs)
    if health_obj is not None:
        _add_evidence(out, _safe_rel(root, health_abs) + "#ssot_status")
        out["findings"].append(f"ssot_status={health_obj.get('ssot_status', 'UNKNOWN')}")
    elif health_err not in {None, "missing"}:
        _add_missing(out, health_rel, health_err)

    if obj is None:
        if out["evidence_refs"]:
            out["status"] = "WARN"
            out["summary"] = "manifest missing; fallback SSOT/state_atomic evidence only"
        else:
            out["status"] = "UNKNOWN"
            out["summary"] = "required manifest missing and no fallback evidence available"

    return _finalize(out)


def factor_health_and_drift_report(
    repo_root: Path,
    factor_manifest_path: str = "reports/research/factor_manifest.json",
    factor_name: str = "",
    baseline_ref: str = "",
) -> dict[str, Any]:
    """Report-only factor drift skeleton with fallback evidence refs."""
    inputs = {
        "factor_manifest_path": factor_manifest_path,
        "factor_name": factor_name,
        "baseline_ref": baseline_ref,
    }
    out = _base_payload("factor_health_and_drift_report", inputs)

    root = Path(repo_root).resolve()

    factor_abs = (root / factor_manifest_path).resolve()
    obj, err = _load_json(factor_abs)
    if obj is None:
        _add_missing(out, factor_manifest_path, err)
    else:
        _add_evidence(out, _safe_rel(root, factor_abs))
        out["status"] = "OK"
        out["summary"] = "factor manifest found; drift metadata surfaced"
        drift_score = obj.get("drift_score", "UNKNOWN")
        out["findings"].extend(
            [
                f"factor_name={obj.get('factor_name') or factor_name or 'UNKNOWN'}",
                f"window={obj.get('window', 'UNKNOWN')}",
                f"drift_score={drift_score}",
            ]
        )
        try:
            if float(drift_score) >= 0.2:
                out["status"] = "WARN"
                out["summary"] = "factor manifest found; drift elevated"
        except Exception:
            pass

    evidence_summary_rel = "reports/research/ml/evidence_summary.json"
    evidence_summary_abs = (root / evidence_summary_rel).resolve()
    summary_obj, summary_err = _load_json(evidence_summary_abs)
    if summary_obj is not None:
        _add_evidence(out, _safe_rel(root, evidence_summary_abs))
        rank_corr = summary_obj.get("rank_corr")
        if rank_corr is not None:
            out["findings"].append(f"ml_rank_corr={rank_corr}")
    elif summary_err not in {None, "missing"}:
        _add_missing(out, evidence_summary_rel, summary_err)

    health_rel = "data/state/system_health_latest.json"
    health_abs = (root / health_rel).resolve()
    health_obj, health_err = _load_json(health_abs)
    if health_obj is not None:
        _add_evidence(out, _safe_rel(root, health_abs) + "#components.freshness")
    elif health_err not in {None, "missing"}:
        _add_missing(out, health_rel, health_err)

    if obj is None:
        if out["evidence_refs"]:
            out["status"] = "WARN"
            out["summary"] = "factor manifest missing; fallback SSOT/report evidence only"
        else:
            out["status"] = "UNKNOWN"
            out["summary"] = "factor manifest missing and no fallback evidence available"

    return _finalize(out)


def strategy_regime_sensitivity_report(
    repo_root: Path,
    regime_report_path: str = "reports/research/regime_sensitivity.json",
    strategy_id: str = "",
    regime_set: str = "",
) -> dict[str, Any]:
    """Report-only regime sensitivity skeleton with state_atomic/SSOT fallback."""
    inputs = {
        "regime_report_path": regime_report_path,
        "strategy_id": strategy_id,
        "regime_set": regime_set,
    }
    out = _base_payload("strategy_regime_sensitivity_report", inputs)

    root = Path(repo_root).resolve()

    regime_abs = (root / regime_report_path).resolve()
    obj, err = _load_json(regime_abs)
    if obj is None:
        _add_missing(out, regime_report_path, err)
    else:
        _add_evidence(out, _safe_rel(root, regime_abs))
        out["status"] = "OK"
        out["summary"] = "regime sensitivity artifact found"
        sensitivity = str(obj.get("sensitivity", "UNKNOWN"))
        out["findings"].extend(
            [
                f"strategy_id={obj.get('strategy_id') or strategy_id or 'UNKNOWN'}",
                f"regime_set={obj.get('regime_set') or regime_set or 'UNKNOWN'}",
                f"sensitivity={sensitivity}",
            ]
        )
        if sensitivity.lower() in {"unstable", "high"}:
            out["status"] = "WARN"
            out["summary"] = "regime sensitivity artifact found; elevated sensitivity flagged"

    for rel, key in [
        ("reports/state_atomic/regime_monitor_latest.json", "status"),
        ("data/state/regime_monitor_latest.json", "overall"),
        ("data/state/system_health_latest.json", "ssot_status"),
    ]:
        abs_path = (root / rel).resolve()
        state_obj, state_err = _load_json(abs_path)
        if state_obj is not None:
            _add_evidence(out, _safe_rel(root, abs_path) + f"#{key}")
            if key in state_obj:
                out["findings"].append(f"{key}={state_obj.get(key)}")
            elif key == "overall":
                out["findings"].append(f"overall={state_obj.get('status', 'UNKNOWN')}")
            continue
        if state_err not in {None, "missing"}:
            _add_missing(out, rel, state_err)

    if obj is None:
        if out["evidence_refs"]:
            out["status"] = "WARN"
            out["summary"] = "regime report missing; fallback state_atomic/SSOT evidence only"
        else:
            out["status"] = "UNKNOWN"
            out["summary"] = "regime report missing and no fallback evidence available"

    return _finalize(out)
