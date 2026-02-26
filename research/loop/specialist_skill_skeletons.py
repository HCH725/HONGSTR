from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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


def _base_payload(skill: str, inputs: dict[str, Any]) -> dict[str, Any]:
    return {
        "skill": skill,
        "status": "UNKNOWN",
        "report_only": True,
        "inputs": inputs,
        "summary": "required research artifact missing or unreadable",
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
    """Skeleton skill: read manifest if present; otherwise return UNKNOWN."""
    inputs = {"manifest_path": manifest_path, "split_ref": split_ref, "run_id": run_id}
    out = _base_payload("backtest_reproducibility_audit", inputs)

    p = (Path(repo_root) / manifest_path).resolve()
    obj, err = _load_json(p)
    out["evidence_refs"].append(manifest_path)
    if obj is None:
        out["missing_artifacts"].append(f"{manifest_path}:{err}")
        return out

    out["status"] = "OK"
    out["summary"] = "manifest found; reproducibility fields surfaced"
    out["findings"] = [
        f"git_commit={obj.get('git_commit', 'UNKNOWN')}",
        f"created_utc={obj.get('created_utc', 'UNKNOWN')}",
        f"split_ref={obj.get('split_ref') or split_ref or 'UNKNOWN'}",
    ]
    return out


def factor_health_and_drift_report(
    repo_root: Path,
    factor_manifest_path: str = "reports/research/factor_manifest.json",
    factor_name: str = "",
    baseline_ref: str = "",
) -> dict[str, Any]:
    """Skeleton skill: report factor drift metadata from manifest if present."""
    inputs = {
        "factor_manifest_path": factor_manifest_path,
        "factor_name": factor_name,
        "baseline_ref": baseline_ref,
    }
    out = _base_payload("factor_health_and_drift_report", inputs)

    p = (Path(repo_root) / factor_manifest_path).resolve()
    obj, err = _load_json(p)
    out["evidence_refs"].append(factor_manifest_path)
    if obj is None:
        out["missing_artifacts"].append(f"{factor_manifest_path}:{err}")
        return out

    out["status"] = "OK"
    out["summary"] = "factor manifest found; drift metadata surfaced"
    out["findings"] = [
        f"factor_name={obj.get('factor_name') or factor_name or 'UNKNOWN'}",
        f"window={obj.get('window', 'UNKNOWN')}",
        f"drift_score={obj.get('drift_score', 'UNKNOWN')}",
    ]
    return out


def strategy_regime_sensitivity_report(
    repo_root: Path,
    regime_report_path: str = "reports/research/regime_sensitivity.json",
    strategy_id: str = "",
    regime_set: str = "",
) -> dict[str, Any]:
    """Skeleton skill: report regime sensitivity artifact status if present."""
    inputs = {
        "regime_report_path": regime_report_path,
        "strategy_id": strategy_id,
        "regime_set": regime_set,
    }
    out = _base_payload("strategy_regime_sensitivity_report", inputs)

    p = (Path(repo_root) / regime_report_path).resolve()
    obj, err = _load_json(p)
    out["evidence_refs"].append(regime_report_path)
    if obj is None:
        out["missing_artifacts"].append(f"{regime_report_path}:{err}")
        return out

    out["status"] = "OK"
    out["summary"] = "regime sensitivity artifact found"
    out["findings"] = [
        f"strategy_id={obj.get('strategy_id') or strategy_id or 'UNKNOWN'}",
        f"regime_set={obj.get('regime_set') or regime_set or 'UNKNOWN'}",
        f"sensitivity={obj.get('sensitivity', 'UNKNOWN')}",
    ]
    return out
