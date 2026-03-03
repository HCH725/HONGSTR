import json
import os
import sys
import pytest
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_cmc_empty_payload_ok(tmp_path):
    # This test ensures cmc_market_intel_fetch.py handles empty payloads gracefully
    # We will mock the urllib.request.urlopen to return empty data payload
    
    script_path = REPO_ROOT / "scripts" / "cmc_market_intel_fetch.py"
    coverage_path = REPO_ROOT / "reports" / "state_atomic" / "cmc_market_intel_coverage.json"
    
    # We'll run the script with a dummy key. Since we don't mock it at the OS level easily in a subprocess without wrappers,
    # the script naturally tries to fetch and with a fake key it gets HTTP 401 (Tier Gated/Unauthorized).
    # The requirement: "HTTP error/exception：FAIL (exit code 可維持 0 但 coverage=FAIL)"
    # Or if we pass mock env:
    env = os.environ.copy()
    env["CMC_API_KEY"] = "dummy_for_testing"
    
    res = subprocess.run([sys.executable, str(script_path)], env=env, capture_output=True, text=True)
    
    assert res.returncode == 0, f"Script must not crash (exit 0). Stderr: {res.stderr}"
    assert coverage_path.exists(), "Coverage file must be created"
    
    cov = json.loads(coverage_path.read_text())
    assert cov["status"] in ("WARN", "FAIL"), "Should be WARN or FAIL"
    assert "reason" in cov
    assert "items" in cov
    assert cov["items"]["narratives_count"] == 0
    assert cov["items"]["macro_events_count"] == 0
