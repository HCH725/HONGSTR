import os
import json
import shutil
from pathlib import Path
import pytest
from scripts.phase4_regime_monitor import resolve_latest_run

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
