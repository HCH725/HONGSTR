import json
import pytest
from pathlib import Path
import subprocess
import os

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_catalog_includes_cmc():
    """
    Test that running refresh_state.sh picks up cmc_market_intel_v1.
    """
    catalog_path = REPO_ROOT / "data" / "state" / "data_catalog_latest.json"
    
    env = os.environ.copy()
    env["CMC_API_KEY"] = "dummy"
    subprocess.run(["python3", "scripts/cmc_market_intel_fetch.py"], env=env, cwd=REPO_ROOT, capture_output=True)
    
    res = subprocess.run(["bash", "scripts/refresh_state.sh"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert res.returncode == 0, f"refresh_state failed: {res.stderr}"
    
    cat_data = json.loads(catalog_path.read_text())
    assert "ts_utc" in cat_data
    assert "datasets" in cat_data
    
    dataset_ids = [ds.get("dataset_id") for ds in cat_data["datasets"]]
    assert "cmc_market_intel_v1" in dataset_ids, f"Catalog did not include cmc_market_intel_v1. Found: {dataset_ids}"
