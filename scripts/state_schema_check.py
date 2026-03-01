#!/usr/bin/env python3
"""
scripts/state_schema_check.py
Validates the presence of SSOT provenance metadata on key output files.
Outputs status to state_schema_check_latest.json (OK/WARN/FAIL) without exception crashes.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

STATE_DIR = Path("data/state")
OUTPUT_FILE = STATE_DIR / "state_schema_check_latest.json"

TARGET_FILES = [
    "system_health_latest.json",
    "freshness_table.json",
    "coverage_matrix_latest.json",
    "brake_health_latest.json",
    "regime_monitor_latest.json",
    "daily_report_latest.json",
]

REQUIRED_KEYS = {
    "schema_version": str,
    "producer_git_sha": str,
    "generated_utc": str,
    "source_inputs": list,
}

def check_file(path: Path) -> dict:
    if not path.exists():
        return {
            "status": "UNKNOWN",
            "missing_keys": list(REQUIRED_KEYS.keys()),
            "reason": "File does not exist"
        }
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return {
            "status": "FAIL",
            "missing_keys": list(REQUIRED_KEYS.keys()),
            "reason": f"Failed to parse JSON: {e}"
        }

    if not isinstance(data, dict):
        return {
            "status": "FAIL",
            "missing_keys": list(REQUIRED_KEYS.keys()),
            "reason": "Root payload is not a dictionary"
        }

    missing_keys = []
    type_errors = []
    for k, expected_type in REQUIRED_KEYS.items():
        if k not in data:
            missing_keys.append(k)
        elif not isinstance(data[k], expected_type):
            type_errors.append(f"{k} (expected {expected_type.__name__})")
        elif k == "schema_version" and data[k] != "1.0":
            type_errors.append(f"schema_version (expected '1.0', got '{data[k]}')")

    if missing_keys or type_errors:
        reasons = []
        if missing_keys:
            reasons.append("Missing: " + ", ".join(missing_keys))
        if type_errors:
            reasons.append("Invalid: " + ", ".join(type_errors))
        return {
            "status": "FAIL",
            "missing_keys": missing_keys,
            "reason": " | ".join(reasons)
        }

    return {
        "status": "PASS",
        "missing_keys": [],
        "reason": None
    }

def main():
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    
    results = {}
    overall_status = "PASS"
    
    for filename in TARGET_FILES:
        filepath = STATE_DIR / filename
        file_result = check_file(filepath)
        results[filename] = file_result
        
        fs = file_result["status"]
        if fs == "FAIL":
            overall_status = "FAIL"
        elif fs == "UNKNOWN" and overall_status != "FAIL":
            overall_status = "WARN"

    # We map PASS to OK for system health compatibility
    if overall_status == "PASS":
        overall_status = "OK"

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    payload = {
        "generated_utc": now_utc,
        "status": overall_status,
        "refresh_hint": "bash scripts/refresh_state.sh",
        "checks": results
    }

    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logging.info(f"Schema check complete. Overall: {overall_status}")
    except Exception as e:
        logging.error(f"Failed to write schema check output: {e}")

if __name__ == "__main__":
    main()
