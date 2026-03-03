from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from research.loop.regime_threshold_calibrator import run_calibration


def _write_policy(path: Path, *, warn: float, fail: float, min_samples: int = 1) -> None:
    payload = {
        "name": "regime_thresholds_v1",
        "metric": "max_drawdown",
        "thresholds": {"warn": warn, "fail": fail},
        "calibration": {
            "mode": "semi_dynamic_weekly_pr",
            "lookback_days": 90,
            "warn_quantile": 0.90,
            "fail_quantile": 0.97,
            "min_samples": min_samples,
            "stale_after_days": 8,
            "last_calibrated_utc": "2026-02-01T00:00:00Z",
            "calibration_status": "STALE",
        },
        "rationale": "test policy",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_summary(repo: Path, rel_run_dir: str, *, ts_utc: str, mdd: float) -> None:
    run_dir = repo / rel_run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "timestamp": ts_utc.replace("Z", ""),
        "max_drawdown": mdd,
        "sharpe": 1.0,
        "trades_count": 30,
        "total_return": 0.1,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")


def test_calibration_output_schema_and_artifacts(tmp_path: Path):
    repo = tmp_path / "repo"
    policy_path = repo / "research/policy/regime_thresholds.json"
    candidate_path = repo / "research/policy/regime_thresholds_candidate.json"
    report_root = repo / "reports/research/regime_threshold_calibration"
    audit_root = repo / "docs/audits"
    _write_policy(policy_path, warn=-0.08, fail=-0.14)

    _write_summary(repo, "data/backtests/2026-02-20/run_a", ts_utc="2026-02-20T00:00:00Z", mdd=-0.05)
    _write_summary(repo, "data/backtests/2026-02-21/run_b", ts_utc="2026-02-21T00:00:00Z", mdd=-0.11)
    _write_summary(repo, "data/backtests/2026-02-22/run_c", ts_utc="2026-02-22T00:00:00Z", mdd=-0.16)

    as_of = datetime(2026, 2, 27, 0, 0, 0, tzinfo=timezone.utc)
    out = run_calibration(
        repo_root=repo,
        policy_path=policy_path,
        candidate_policy_path=candidate_path,
        report_root=report_root,
        audit_root=audit_root,
        as_of_utc=as_of,
        write_runtime_reports=True,
        prepare_pr=True,
    )

    payload = out.report_payload
    assert payload["report_only"] is True
    assert set(payload.keys()) >= {
        "generated_utc",
        "sample_period",
        "method",
        "recommended_thresholds",
        "diff_vs_current",
        "impact",
    }
    assert payload["sample_period"]["sample_count"] == 3
    assert out.candidate_policy["thresholds"]["warn"] <= 0
    assert out.candidate_policy["thresholds"]["fail"] <= out.candidate_policy["thresholds"]["warn"]
    assert "candidate_policy_json" in out.output_paths
    assert "report_json" in out.output_paths
    assert "report_markdown" in out.output_paths
    assert "active_policy_json" in out.output_paths
    assert "audit_markdown" in out.output_paths
    assert (repo / out.output_paths["audit_markdown"]).exists()


def test_calibration_policy_diff_and_impact_change(tmp_path: Path):
    repo = tmp_path / "repo"
    policy_path = repo / "research/policy/regime_thresholds.json"
    _write_policy(policy_path, warn=-0.03, fail=-0.05, min_samples=1)

    for idx, mdd in enumerate([-0.02, -0.03, -0.06, -0.09, -0.12], start=1):
        _write_summary(
            repo,
            f"data/backtests/2026-02-{idx+10:02d}/run_{idx}",
            ts_utc=f"2026-02-{idx+10:02d}T00:00:00Z",
            mdd=mdd,
        )

    out = run_calibration(
        repo_root=repo,
        policy_path=policy_path,
        candidate_policy_path=repo / "research/policy/regime_thresholds_candidate.json",
        report_root=repo / "reports/research/regime_threshold_calibration",
        audit_root=repo / "docs/audits",
        as_of_utc=datetime(2026, 2, 27, 0, 0, 0, tzinfo=timezone.utc),
        write_runtime_reports=False,
        prepare_pr=False,
    )

    diff = out.report_payload["diff_vs_current"]
    impact = out.report_payload["impact"]
    assert isinstance(diff["warn_delta"], float)
    assert isinstance(diff["fail_delta"], float)
    assert impact["sample_count"] == 5
    assert 0.0 <= impact["current"]["fail_ratio"] <= 1.0
    assert 0.0 <= impact["recommended"]["fail_ratio"] <= 1.0
    assert isinstance(impact["delta_fail_ratio"], float)


def test_calibration_no_lookahead_ignores_future_samples(tmp_path: Path):
    repo = tmp_path / "repo"
    policy_path = repo / "research/policy/regime_thresholds.json"
    _write_policy(policy_path, warn=-0.08, fail=-0.14, min_samples=1)

    _write_summary(repo, "data/backtests/2026-02-20/run_a", ts_utc="2026-02-20T00:00:00Z", mdd=-0.05)
    _write_summary(repo, "data/backtests/2026-02-21/run_b", ts_utc="2026-02-21T00:00:00Z", mdd=-0.06)
    _write_summary(repo, "data/backtests/2026-02-22/run_c", ts_utc="2026-02-22T00:00:00Z", mdd=-0.07)
    # Future sample must be excluded by no-lookahead filter.
    _write_summary(repo, "data/backtests/2026-03-10/run_future", ts_utc="2026-03-10T00:00:00Z", mdd=-0.90)

    out = run_calibration(
        repo_root=repo,
        policy_path=policy_path,
        candidate_policy_path=repo / "research/policy/regime_thresholds_candidate.json",
        report_root=repo / "reports/research/regime_threshold_calibration",
        audit_root=repo / "docs/audits",
        as_of_utc=datetime(2026, 2, 27, 0, 0, 0, tzinfo=timezone.utc),
        write_runtime_reports=False,
        prepare_pr=False,
    )

    sample = out.report_payload["sample_period"]
    assert sample["sample_count"] == 3
    assert sample["end_utc"] <= "2026-02-27T00:00:00Z"
    # If future sample leaked in, fail threshold would collapse near -0.90.
    assert out.candidate_policy["thresholds"]["fail"] > -0.5
