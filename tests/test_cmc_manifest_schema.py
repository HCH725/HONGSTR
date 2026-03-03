import json
import os
import pytest
from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_cmc_manifest_schema():
    script_path = REPO_ROOT / "scripts" / "cmc_market_intel_fetch.py"
    manifest_path = REPO_ROOT / "reports" / "state_atomic" / "manifests" / "cmc_market_intel_v1.json"
    
    # Trigger run to ensure manifest exists
    env = os.environ.copy()
    env["CMC_API_KEY"] = "dummy"
    subprocess.run([sys.executable, str(script_path)], env=env, capture_output=True)
    
    assert manifest_path.exists(), "Manifest should be created"
    manifest = json.loads(manifest_path.read_text())
    
    required_keys = ["dataset_id", "schema_version", "producer", "cadence", 
                     "path_patterns", "symbols", "metrics", "periods", "sources", "provenance"]
    for k in required_keys:
        assert k in manifest, f"Missing required key: {k}"
        
    assert manifest["dataset_id"] == "cmc_market_intel_v1"
    assert "narratives" in manifest["metrics"]
    assert "macro_events" in manifest["metrics"]
    assert manifest["cadence"] == "daily"
    assert "root" in manifest["path_patterns"]
    assert "template" in manifest["path_patterns"]
