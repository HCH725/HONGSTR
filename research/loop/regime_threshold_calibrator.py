from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_POLICY_PATH = REPO_ROOT / "research/policy/regime_thresholds.json"
DEFAULT_CANDIDATE_POLICY_PATH = REPO_ROOT / "research/policy/regime_thresholds_candidate.json"
DEFAULT_REPORT_ROOT = REPO_ROOT / "reports/research/regime_threshold_calibration"
DEFAULT_AUDIT_ROOT = REPO_ROOT / "docs/audits"
BACKTEST_SUMMARY_GLOB = "data/backtests/**/summary.json"


@dataclass
class CalibrationResult:
    report_payload: dict[str, Any]
    candidate_policy: dict[str, Any]
    output_paths: dict[str, str]


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _parse_iso_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(raw: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(raw)
    return digest.hexdigest()


def _rel_or_abs(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _load_policy(path: Path) -> tuple[dict[str, Any], str]:
    if not path.exists():
        policy = {
            "name": "regime_thresholds_v1",
            "metric": "max_drawdown",
            "thresholds": {"warn": -0.08, "fail": -0.14},
            "calibration": {
                "lookback_days": 90,
                "warn_quantile": 0.90,
                "fail_quantile": 0.97,
                "min_samples": 30,
                "stale_after_days": 8,
                "last_calibrated_utc": None,
                "calibration_status": "UNKNOWN",
            },
            "rationale": "Policy file missing fallback defaults.",
        }
        return policy, "missing_policy"
    try:
        raw = path.read_bytes()
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("policy_not_dict")
        return obj, _sha256_bytes(raw)
    except Exception:
        policy = {
            "name": "regime_thresholds_v1",
            "metric": "max_drawdown",
            "thresholds": {"warn": -0.08, "fail": -0.14},
            "calibration": {
                "lookback_days": 90,
                "warn_quantile": 0.90,
                "fail_quantile": 0.97,
                "min_samples": 30,
                "stale_after_days": 8,
                "last_calibrated_utc": None,
                "calibration_status": "UNKNOWN",
            },
            "rationale": "Policy unreadable fallback defaults.",
        }
        return policy, "unreadable_policy"


def _calibration_status(last_calibrated_utc: Any, stale_after_days: int, *, now_utc: datetime) -> str:
    last_dt = _parse_iso_utc(last_calibrated_utc)
    if not last_dt:
        return "UNKNOWN"
    age_days = (now_utc - last_dt).total_seconds() / 86400.0
    if age_days <= max(1, int(stale_after_days)):
        return "OK"
    return "STALE"


def _classify_mdd(max_drawdown: float, warn_threshold: float, fail_threshold: float) -> str:
    if max_drawdown < fail_threshold:
        return "FAIL"
    if max_drawdown < warn_threshold:
        return "WARN"
    return "OK"


def _load_backtest_records(
    repo_root: Path,
    *,
    as_of_utc: datetime,
    lookback_days: int,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    backtest_root = repo_root / "data/backtests"
    if not backtest_root.exists():
        return records

    window_start = as_of_utc - timedelta(days=max(1, int(lookback_days)))
    for summary_path in backtest_root.glob("**/summary.json"):
        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
        except Exception:
            continue

        mdd_raw = payload.get("max_drawdown")
        try:
            mdd = float(mdd_raw)
        except Exception:
            continue

        ts = (
            _parse_iso_utc(payload.get("timestamp"))
            or _parse_iso_utc(payload.get("ts_utc"))
            or _parse_iso_utc(payload.get("generated_utc"))
        )
        if ts is None:
            try:
                ts = datetime.fromtimestamp(summary_path.stat().st_mtime, tz=timezone.utc)
            except Exception:
                continue

        # No lookahead: strictly ignore any sample newer than as_of_utc.
        if ts > as_of_utc:
            continue
        if ts < window_start:
            continue

        records.append(
            {
                "timestamp_utc": _iso_utc(ts),
                "max_drawdown": mdd,
                "path": str(summary_path.relative_to(repo_root)).replace("\\", "/"),
            }
        )

    records.sort(key=lambda r: r["timestamp_utc"])
    return records


def _recommend_thresholds(
    records: list[dict[str, Any]],
    *,
    warn_quantile: float,
    fail_quantile: float,
    fallback_warn: float,
    fallback_fail: float,
) -> tuple[float, float]:
    if not records:
        return fallback_warn, fallback_fail

    severities = [abs(min(0.0, float(row.get("max_drawdown", 0.0)))) for row in records]
    warn_severity = float(np.quantile(severities, warn_quantile))
    fail_severity = float(np.quantile(severities, fail_quantile))

    warn_threshold = -abs(warn_severity)
    fail_threshold = -abs(fail_severity)
    if fail_threshold > warn_threshold:
        fail_threshold = warn_threshold
    return warn_threshold, fail_threshold


def _status_counts(records: list[dict[str, Any]], warn_threshold: float, fail_threshold: float) -> dict[str, int]:
    counts = {"OK": 0, "WARN": 0, "FAIL": 0}
    for row in records:
        st = _classify_mdd(float(row.get("max_drawdown", 0.0)), warn_threshold, fail_threshold)
        counts[st] = counts.get(st, 0) + 1
    return counts


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def run_calibration(
    repo_root: Path,
    *,
    policy_path: Path,
    candidate_policy_path: Path,
    report_root: Path,
    audit_root: Path,
    as_of_utc: datetime | None = None,
    write_runtime_reports: bool = True,
    prepare_pr: bool = False,
) -> CalibrationResult:
    root = Path(repo_root).resolve()
    now = as_of_utc or datetime.now(timezone.utc)
    now_utc = _iso_utc(now)

    current_policy, current_policy_sha = _load_policy(policy_path)
    thresholds = current_policy.get("thresholds", {}) if isinstance(current_policy.get("thresholds"), dict) else {}
    calibration_cfg = current_policy.get("calibration", {}) if isinstance(current_policy.get("calibration"), dict) else {}

    current_warn = _as_float(thresholds.get("warn"), -0.08)
    current_fail = _as_float(thresholds.get("fail"), -0.14)
    lookback_days = int(_as_float(calibration_cfg.get("lookback_days"), 90))
    warn_quantile = _as_float(calibration_cfg.get("warn_quantile"), 0.90)
    fail_quantile = _as_float(calibration_cfg.get("fail_quantile"), 0.97)
    min_samples = int(_as_float(calibration_cfg.get("min_samples"), 30))
    stale_after_days = int(_as_float(calibration_cfg.get("stale_after_days"), 8))

    records = _load_backtest_records(root, as_of_utc=now, lookback_days=lookback_days)
    sample_count = len(records)

    if sample_count >= max(1, min_samples):
        rec_warn, rec_fail = _recommend_thresholds(
            records,
            warn_quantile=warn_quantile,
            fail_quantile=fail_quantile,
            fallback_warn=current_warn,
            fallback_fail=current_fail,
        )
        method_status = "OK"
        method_note = "calibrated_from_historical_distribution"
    else:
        rec_warn, rec_fail = current_warn, current_fail
        method_status = "WARN"
        method_note = "insufficient_samples_keep_current_thresholds"

    current_counts = _status_counts(records, current_warn, current_fail)
    recommended_counts = _status_counts(records, rec_warn, rec_fail)

    period_start = records[0]["timestamp_utc"] if records else None
    period_end = records[-1]["timestamp_utc"] if records else None
    prev_last_calibrated = calibration_cfg.get("last_calibrated_utc")
    prev_cal_status = _calibration_status(prev_last_calibrated, stale_after_days, now_utc=now)

    candidate_policy = dict(current_policy)
    candidate_policy["metric"] = "max_drawdown"
    candidate_policy["thresholds"] = {
        "warn": round(rec_warn, 6),
        "fail": round(rec_fail, 6),
    }
    candidate_cal = dict(calibration_cfg)
    candidate_cal_status = "OK" if method_status == "OK" else "WARN"
    candidate_cal.update(
        {
            "mode": "semi_dynamic_weekly_pr",
            "lookback_days": lookback_days,
            "warn_quantile": warn_quantile,
            "fail_quantile": fail_quantile,
            "min_samples": min_samples,
            "stale_after_days": stale_after_days,
            "last_calibrated_utc": now_utc,
            "calibration_status": candidate_cal_status,
            "sample_count": sample_count,
            "sample_period_start_utc": period_start,
            "sample_period_end_utc": period_end,
        }
    )
    candidate_policy["calibration"] = candidate_cal
    candidate_policy["rationale"] = (
        "Weekly semi-dynamic calibration (reviewed by PR) based on backtest summary max_drawdown distribution."
    )
    candidate_policy["provenance"] = {
        "source_glob": BACKTEST_SUMMARY_GLOB,
        "calibrator_path": "research/loop/regime_threshold_calibrator.py",
        "policy_review": "human_approved_via_pr",
        "previous_policy_sha256": current_policy_sha,
    }

    report_payload = {
        "generated_utc": now_utc,
        "as_of_utc": now_utc,
        "report_only": True,
        "policy_path": _rel_or_abs(policy_path, root),
        "candidate_policy_path": _rel_or_abs(candidate_policy_path, root),
        "sample_period": {
            "lookback_days": lookback_days,
            "start_utc": period_start,
            "end_utc": period_end,
            "sample_count": sample_count,
        },
        "method": {
            "metric": "max_drawdown",
            "transform": "severity=abs(min(0,mdd))",
            "warn_quantile": warn_quantile,
            "fail_quantile": fail_quantile,
            "min_samples": min_samples,
            "no_lookahead_rule": "sample.timestamp <= as_of_utc",
            "status": method_status,
            "note": method_note,
        },
        "current_thresholds": {
            "warn": current_warn,
            "fail": current_fail,
            "policy_sha256": current_policy_sha,
            "last_calibrated_utc": prev_last_calibrated,
            "calibration_status": prev_cal_status,
        },
        "recommended_thresholds": {
            "warn": round(rec_warn, 6),
            "fail": round(rec_fail, 6),
        },
        "diff_vs_current": {
            "warn_delta": round(rec_warn - current_warn, 6),
            "fail_delta": round(rec_fail - current_fail, 6),
        },
        "impact": {
            "sample_count": sample_count,
            "current": {
                "counts": current_counts,
                "fail_ratio": round(_ratio(current_counts["FAIL"], sample_count), 6),
            },
            "recommended": {
                "counts": recommended_counts,
                "fail_ratio": round(_ratio(recommended_counts["FAIL"], sample_count), 6),
            },
            "delta_fail_ratio": round(
                _ratio(recommended_counts["FAIL"], sample_count) - _ratio(current_counts["FAIL"], sample_count),
                6,
            ),
        },
        "rationale": (
            "Semi-dynamic weekly calibration proposes thresholds only; activation requires manual policy PR merge."
        ),
    }

    output_paths: dict[str, str] = {}
    candidate_policy_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_policy_path.write_text(json.dumps(candidate_policy, indent=2), encoding="utf-8")
    output_paths["candidate_policy_json"] = _rel_or_abs(candidate_policy_path, root)

    stamp = now.strftime("%Y%m%d")
    if write_runtime_reports:
        runtime_dir = report_root / stamp
        runtime_dir.mkdir(parents=True, exist_ok=True)
        runtime_json = runtime_dir / "regime_threshold_calibration.json"
        runtime_md = runtime_dir / "regime_threshold_calibration.md"
        runtime_json.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
        runtime_md.write_text(_render_markdown(report_payload), encoding="utf-8")
        output_paths["report_json"] = _rel_or_abs(runtime_json, root)
        output_paths["report_markdown"] = _rel_or_abs(runtime_md, root)

    if prepare_pr:
        policy_path.parent.mkdir(parents=True, exist_ok=True)
        policy_path.write_text(json.dumps(candidate_policy, indent=2), encoding="utf-8")
        output_paths["active_policy_json"] = _rel_or_abs(policy_path, root)

        audit_root.mkdir(parents=True, exist_ok=True)
        audit_json = audit_root / f"regime_threshold_calibration_{stamp}.json"
        audit_md = audit_root / f"regime_threshold_calibration_{stamp}.md"
        audit_json.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
        audit_md.write_text(_render_markdown(report_payload), encoding="utf-8")
        output_paths["audit_json"] = _rel_or_abs(audit_json, root)
        output_paths["audit_markdown"] = _rel_or_abs(audit_md, root)

    return CalibrationResult(
        report_payload=report_payload,
        candidate_policy=candidate_policy,
        output_paths=output_paths,
    )


def _render_markdown(payload: dict[str, Any]) -> str:
    sample = payload.get("sample_period", {}) if isinstance(payload.get("sample_period"), dict) else {}
    method = payload.get("method", {}) if isinstance(payload.get("method"), dict) else {}
    current = payload.get("current_thresholds", {}) if isinstance(payload.get("current_thresholds"), dict) else {}
    recommended = payload.get("recommended_thresholds", {}) if isinstance(payload.get("recommended_thresholds"), dict) else {}
    diff = payload.get("diff_vs_current", {}) if isinstance(payload.get("diff_vs_current"), dict) else {}
    impact = payload.get("impact", {}) if isinstance(payload.get("impact"), dict) else {}
    impact_curr = impact.get("current", {}) if isinstance(impact.get("current"), dict) else {}
    impact_next = impact.get("recommended", {}) if isinstance(impact.get("recommended"), dict) else {}

    lines = [
        "# Regime Threshold Calibration Audit",
        "",
        f"- generated_utc: {payload.get('generated_utc')}",
        f"- as_of_utc: {payload.get('as_of_utc')}",
        f"- report_only: {payload.get('report_only')}",
        "",
        "## Sample Window",
        f"- lookback_days: {sample.get('lookback_days')}",
        f"- start_utc: {sample.get('start_utc')}",
        f"- end_utc: {sample.get('end_utc')}",
        f"- sample_count: {sample.get('sample_count')}",
        "",
        "## Method",
        f"- metric: {method.get('metric')}",
        f"- transform: {method.get('transform')}",
        f"- warn_quantile: {method.get('warn_quantile')}",
        f"- fail_quantile: {method.get('fail_quantile')}",
        f"- no_lookahead_rule: {method.get('no_lookahead_rule')}",
        f"- status: {method.get('status')} ({method.get('note')})",
        "",
        "## Thresholds",
        f"- current WARN/FAIL: {current.get('warn')} / {current.get('fail')}",
        f"- recommended WARN/FAIL: {recommended.get('warn')} / {recommended.get('fail')}",
        f"- delta WARN/FAIL: {diff.get('warn_delta')} / {diff.get('fail_delta')}",
        "",
        "## Expected Impact (Historical)",
        f"- current FAIL ratio: {impact_curr.get('fail_ratio')}",
        f"- recommended FAIL ratio: {impact_next.get('fail_ratio')}",
        f"- delta FAIL ratio: {impact.get('delta_fail_ratio')}",
        "",
        "## Safety",
        "- Semi-dynamic policy flow: calibration proposes candidate only.",
        "- Active policy changes require reviewed PR merge.",
        "",
        "## Rollback",
        "```bash",
        "git revert <merge_commit_sha>",
        "```",
    ]
    return "\n".join(lines) + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Regime threshold semi-dynamic calibration (report_only).")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--candidate-policy-path", default=str(DEFAULT_CANDIDATE_POLICY_PATH))
    parser.add_argument("--report-root", default=str(DEFAULT_REPORT_ROOT))
    parser.add_argument("--audit-root", default=str(DEFAULT_AUDIT_ROOT))
    parser.add_argument("--as-of-utc", default="", help="ISO UTC timestamp, e.g. 2026-02-27T00:00:00Z")
    parser.add_argument("--prepare-pr", action="store_true", help="Also update active policy and write docs/audits artifacts.")
    parser.add_argument("--skip-runtime-reports", action="store_true", help="Do not write reports/research runtime artifacts.")
    parser.add_argument("--pr-mode", action="store_true", help="Equivalent to --prepare-pr --skip-runtime-reports.")
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    policy_path = Path(args.policy_path)
    if not policy_path.is_absolute():
        policy_path = (repo_root / policy_path).resolve()
    candidate_policy_path = Path(args.candidate_policy_path)
    if not candidate_policy_path.is_absolute():
        candidate_policy_path = (repo_root / candidate_policy_path).resolve()
    report_root = Path(args.report_root)
    if not report_root.is_absolute():
        report_root = (repo_root / report_root).resolve()
    audit_root = Path(args.audit_root)
    if not audit_root.is_absolute():
        audit_root = (repo_root / audit_root).resolve()

    as_of_utc = _parse_iso_utc(args.as_of_utc) if args.as_of_utc else None
    prepare_pr = bool(args.prepare_pr or args.pr_mode)
    skip_runtime_reports = bool(args.skip_runtime_reports or args.pr_mode)

    result = run_calibration(
        repo_root=repo_root,
        policy_path=policy_path,
        candidate_policy_path=candidate_policy_path,
        report_root=report_root,
        audit_root=audit_root,
        as_of_utc=as_of_utc,
        write_runtime_reports=not skip_runtime_reports,
        prepare_pr=prepare_pr,
    )

    print("Regime threshold calibration finished.")
    for key, path in sorted(result.output_paths.items()):
        print(f"- {key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
