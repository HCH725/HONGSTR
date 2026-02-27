import json
import os
from datetime import datetime

def test_regime_timeline_safety():
    policy_path = "research/policy/regime_timeline.json"
    assert os.path.exists(policy_path), f"Policy file missing: {policy_path}"
    
    with open(policy_path, "r") as f:
        data = json.load(f)
        
    # Schema check
    assert data.get("schema_version") == "regime_timeline.v1"
    assert "regimes" in data
    regimes = data["regimes"]
    
    allowed_names = {"bull", "bear", "sideways"}
    last_end = None
    
    for i, r in enumerate(regimes):
        # Key presence
        for key in ["name", "start_utc", "end_utc", "source"]:
            assert key in r, f"Missing key '{key}' in regime index {i}"
            
        assert r["name"] in allowed_names, f"Invalid name '{r['name']}' in index {i}"
        
        # Datetime format & logic
        start = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ")
        end = datetime.strptime(r["end_utc"], "%Y-%m-%dT%H:%M:%SZ")
        assert start < end, f"Start must be before end in index {i}"
        
        # Non-overlapping & Sorted check
        if last_end is not None:
            assert start >= last_end, f"Overlapping or unsorted regimes at index {i}: {start} < {last_end}"
            
        last_end = end

    print(f"Validated {len(regimes)} regime intervals.")

if __name__ == "__main__":
    test_regime_timeline_safety()
