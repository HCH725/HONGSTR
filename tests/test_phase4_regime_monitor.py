import os
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pytest
from scripts.phase4_regime_monitor import resolve_latest_run, load_regime_policy, evaluate

def test_resolve_latest_run_prioritization(tmp_path, monkeypatch):
    # Mock REPO
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("scripts.phase4_regime_monitor.REPO", repo)
    
    backtest_root = repo / "data/backtests"
    backtest_root.mkdir(parents=True)
    
    # 1. Create a fragment run (latest)
    frag_dir = backtest_root / "2026-02-24" / "fragment_run"
    frag_dir.mkdir(parents=True)
    frag_summary = frag_dir / "summary.json"
    frag_summary.write_text("{}")
    
    # 2. Create a full run (older)
    full_dir = backtest_root / "2026-02-23" / "full_run"
    full_dir.mkdir(parents=True)
    full_summary = full_dir / "summary.json"
    full_summary.write_text("{}")
    (full_dir / "selection.json").write_text("{}")
    
    # Set mtime: fragment is newer than full
    os.utime(frag_summary, (1700000000, 1700000000))
    os.utime(full_summary, (1600000000, 1600000000))
    
    # Run resolution
    run_dir, summary_p, reason = resolve_latest_run()
    
    assert reason == "full_run"
    assert run_dir == full_dir
    assert summary_p == full_summary
    assert str(summary_p.relative_to(repo)) != ""

def test_resolve_latest_run_fallback(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("scripts.phase4_regime_monitor.REPO", repo)
    
    backtest_root = repo / "data/backtests"
    backtest_root.mkdir(parents=True)
    
    # Create only fragment runs
    frag_dir = backtest_root / "2026-02-24" / "fragment_run"
    frag_dir.mkdir(parents=True)
    frag_summary = frag_dir / "summary.json"
    frag_summary.write_text("{}")
    
    run_dir, summary_p, reason = resolve_latest_run()
    
    assert reason == "fallback_fragment"
    assert run_dir == frag_dir
    assert summary_p == frag_summary

def test_resolve_latest_run_no_data(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr("scripts.phase4_regime_monitor.REPO", repo)
    
    run_dir, summary_p, reason = resolve_latest_run()
    assert reason == "no_data"


def test_load_regime_policy_reads_calibration_metadata(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    policy_path = repo / "research/policy/regime_thresholds.json"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        json.dumps(
            {
                "name": "regime_thresholds_v1",
                "thresholds": {"warn": -0.08, "fail": -0.14},
                "calibration": {
                    "stale_after_days": 7,
                    "last_calibrated_utc": "2026-02-01T00:00:00Z",
                    "calibration_status": "STALE",
                },
                "rationale": "weekly reviewed policy",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("scripts.phase4_regime_monitor.REGIME_POLICY_PATH", policy_path)

    info = load_regime_policy(datetime(2026, 2, 27, 0, 0, 0, tzinfo=timezone.utc))
    assert info["available"] is True
    assert info["mdd_warn"] == -0.08
    assert info["mdd_fail"] == -0.14
    assert info["calibration_status"] == "STALE"
    assert info["last_calibrated_utc"] == "2026-02-01T00:00:00Z"


def test_evaluate_uses_policy_source_for_mdd_event():
    thresholds = {
        "sharpe": {"warn": -999.0, "fail": -1000.0},  # disable sharpe alerts
        "trades": {"warn_gate": -1},  # disable trade alerts
        "mdd": {"p80": -0.12, "p95": -0.2},
    }
    phase3_source = {"path": "reports/strategy_research/phase3/phase3_results.json", "sha": "phase3sha", "version": "phase3"}
    mdd_source = {
        "warn": -0.05,
        "fail": -0.1,
        "path": "research/policy/regime_thresholds.json",
        "sha": "policysha",
        "version": "regime_thresholds_v1",
        "label": "approved regime policy",
    }
    current = {"sharpe": 10.0, "trades_count": 100, "max_drawdown": -0.2}

    status, reasons, primary = evaluate(current, thresholds, phase3_source=phase3_source, mdd_source=mdd_source)
    assert status == "FAIL"
    assert isinstance(reasons, list) and reasons
    assert primary["metric"] == "max_drawdown"
    assert primary["threshold_source_path"] == "research/policy/regime_thresholds.json"
    assert primary["threshold_policy_sha"] == "policysha"
