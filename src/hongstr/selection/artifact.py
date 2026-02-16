import json
import os
from dateutil import parser
from hongstr.alerts.telegram import send_alert

def load_selection_artifact(path: str, expected_portfolio_id: str = "HONG") -> dict:
    """
    Load and validate selection artifact strictly.
    Gate-1: FAIL-CLOSED validation.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Selection artifact not found at {path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in selection artifact: {e}")

    # 1. Schema Version
    if data.get("schema_version") != "selection_artifact_v1":
        raise ValueError(f"Invalid schema_version: {data.get('schema_version')}")

    # 2. Portfolio ID
    pid = data.get("portfolio_id")
    if pid != expected_portfolio_id:
        raise ValueError(f"Portfolio ID mismatch: Expected {expected_portfolio_id}, Got {pid}")

    # 3. Timestamp (GMT+8 aware)
    ts_str = data.get("timestamp_gmt8")
    if not ts_str:
        raise ValueError("Missing timestamp_gmt8")
    
    try:
        dt = parser.parse(ts_str)
        if dt.tzinfo is None:
             raise ValueError("timestamp_gmt8 must be timezone-aware")
        # Check offset approx +08:00 (allowing name variations)
        # We can strict check offset
        if dt.utcoffset().total_seconds() != 8 * 3600:
             raise ValueError(f"timestamp_gmt8 must be +08:00 (GMT+8). Got offset {dt.utcoffset()}")
    except Exception as e:
        raise ValueError(f"Invalid timestamp_gmt8: {e}")

    # 4. Selection structure
    sel = data.get("selection")
    if not isinstance(sel, dict):
        raise ValueError("Field 'selection' must be object")
    
    for k in ["BULL", "BEAR", "NEUTRAL"]:
        if k not in sel:
             raise ValueError(f"Missing selection key: {k}")
        if not isinstance(sel[k], list):
             raise ValueError(f"Selection {k} must be list")

    # 5. Policy exists
    if "policy" not in data:
         raise ValueError("Missing field 'policy'")

    # 6. Metadata git_commit
    meta = data.get("metadata", {})
    if not isinstance(meta, dict):
         raise ValueError("Field 'metadata' must be object")
    if "git_commit" not in meta:
         raise ValueError("Missing metadata.git_commit")
    if not isinstance(meta["git_commit"], str):
         raise ValueError("metadata.git_commit must be string")

    return data
