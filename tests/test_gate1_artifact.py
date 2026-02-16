import pytest
import json
import os
from datetime import datetime
from hongstr.selection.artifact import load_selection_artifact
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("Asia/Taipei")
except ImportError:
    import pytz
    TZ = pytz.timezone("Asia/Taipei")

def test_gate1_valid_artifact(tmp_path):
    artifact = {
        "schema_version": "selection_artifact_v1",
        "portfolio_id": "HONG",
        "timestamp_gmt8": datetime.now(TZ).isoformat(),
        "selection": {"BULL": [], "BEAR": [], "NEUTRAL": []},
        "policy": {},
        "metadata": {"git_commit": "test"}
    }
    path = tmp_path / "valid.json"
    with open(path, "w") as f:
        json.dump(artifact, f)
    
    data = load_selection_artifact(str(path), "HONG")
    assert data["portfolio_id"] == "HONG"

def test_gate1_invalid_schema(tmp_path):
    artifact = {
        "schema_version": "v0",
        "portfolio_id": "HONG",
        "timestamp_gmt8": datetime.now(TZ).isoformat(),
        "selection": {"BULL": [], "BEAR": [], "NEUTRAL": []},
        "policy": {},
        "metadata": {"git_commit": "test"}
    }
    path = tmp_path / "invalid_schema.json"
    with open(path, "w") as f:
        json.dump(artifact, f)
    
    with pytest.raises(ValueError, match="Invalid schema_version"):
        load_selection_artifact(str(path), "HONG")

def test_gate1_portfolio_mismatch(tmp_path):
    artifact = {
        "schema_version": "selection_artifact_v1",
        "portfolio_id": "LAB",
        "timestamp_gmt8": datetime.now(TZ).isoformat(),
        "selection": {"BULL": [], "BEAR": [], "NEUTRAL": []},
        "policy": {},
        "metadata": {"git_commit": "test"}
    }
    path = tmp_path / "mismatch.json"
    with open(path, "w") as f:
        json.dump(artifact, f)
    
    with pytest.raises(ValueError, match="Portfolio ID mismatch"):
        load_selection_artifact(str(path), "HONG")

def test_gate1_missing_commit(tmp_path):
    artifact = {
        "schema_version": "selection_artifact_v1",
        "portfolio_id": "HONG",
        "timestamp_gmt8": datetime.now(TZ).isoformat(),
        "selection": {"BULL": [], "BEAR": [], "NEUTRAL": []},
        "policy": {},
        "metadata": {} 
    }
    path = tmp_path / "no_commit.json"
    with open(path, "w") as f:
        json.dump(artifact, f)
    
    with pytest.raises(ValueError, match="Missing metadata.git_commit"):
        load_selection_artifact(str(path), "HONG")
