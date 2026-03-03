import json
import os
import time
from pathlib import Path
import pytest

from _local.telegram_cp.skills.run_integrity_report import generate_run_integrity_report
from _local.telegram_cp.skills.worker_acceptance_check import generate_worker_acceptance_check

def test_run_integrity_report(tmp_path):
    # Setup mock structure
    reports_dir = tmp_path / "reports/state_atomic"
    reports_dir.mkdir(parents=True)
    
    brake_health_path = reports_dir / "brake_health_latest.json"
    
    # 1. Test missing brake health
    res = generate_run_integrity_report(tmp_path)
    assert res["status"] == "WARN"
    
    # Setup dummy brake health pointing to a run dir
    run_dir = "data/backtests/2026-02-28/test_run"
    brake_data = {
        "results": [
            {"item": "Backtest summary.json", "path": f"{run_dir}/summary.json"}
        ]
    }
    with open(brake_health_path, "w") as f:
        json.dump(brake_data, f)
        
    # 2. Test missing run dir
    res = generate_run_integrity_report(tmp_path)
    assert res["status"] == "FAIL"
    
    # Setup complete run dir
    abs_run_dir = tmp_path / run_dir
    abs_run_dir.mkdir(parents=True)
    
    # Missing some files -> WARN
    (abs_run_dir / "summary.json").write_text(json.dumps({"metadata": {"regime_slice": "bull"}}))
    res = generate_run_integrity_report(tmp_path)
    assert res["status"] == "WARN"
    assert "Missing files" in res["details"][0]
    
    # Provide all files
    (abs_run_dir / "selection.json").write_text("{}")
    (abs_run_dir / "gate.json").write_text("{}")
    (abs_run_dir / "leaderboard.json").write_text(json.dumps([{"strategy": "A"}]))
    
    res = generate_run_integrity_report(tmp_path)
    assert res["status"] == "OK"
    assert res["leaderboard_ok"] is True
    assert res["regime_slice_found"] is True

def test_worker_acceptance_check(tmp_path):
    # 1. Missing directory -> Graceful OK
    res = generate_worker_acceptance_check(tmp_path)
    assert res["status"] == "OK"
    assert "local-only" in res["details"][0]
    
    # Setup worker dir
    workers_dir = tmp_path / "_local/worker_state_workers"
    workers_dir.mkdir(parents=True)
    
    # 2. Empty directory -> OK
    res = generate_worker_acceptance_check(tmp_path)
    assert res["status"] == "OK"
    
    # 3. Add a healthy worker
    w1_dir = workers_dir / "worker1"
    w1_dir.mkdir()
    hb = {"role": "research"}
    with open(w1_dir / "worker_heartbeat.json", "w") as f:
        json.dump(hb, f)
        
    res = generate_worker_acceptance_check(tmp_path)
    assert res["status"] == "OK"
    assert "worker1" in res["workers"]
    assert res["workers"]["worker1"]["status"] == "OK"
    
    # 4. Add a stale worker
    w2_dir = workers_dir / "worker2"
    w2_dir.mkdir()
    w2_hb_path = w2_dir / "worker_heartbeat.json"
    with open(w2_hb_path, "w") as f:
        json.dump(hb, f)
        
    # Manually set mtime to 3 hours ago
    stale_time = time.time() - 10800
    os.utime(w2_hb_path, (stale_time, stale_time))
    
    res = generate_worker_acceptance_check(tmp_path)
    assert res["status"] == "WARN"
    assert res["workers"]["worker2"]["status"] == "WARN"
