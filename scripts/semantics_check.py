#!/usr/bin/env python3
"""
scripts/semantics_check.py
Compares current Semantics Version with coverage table. 
Stamps NEEDS_REBASE if out of date. Read-only on engine. Exit 0.
"""
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ATOMIC_COVERAGE_FILE = Path("reports/state_atomic/coverage_table.jsonl")
LEGACY_STATE_FILE = Path("data/state/coverage_table.jsonl")
SEMANTICS_FILE = Path("configs/semantics_version.json")

def main():
    if not SEMANTICS_FILE.exists():
        logging.warning("No semantics_version.json found. Exiting.")
        return

    try:
        with open(SEMANTICS_FILE, "r") as f:
            current_version = json.load(f).get("version", "sem_v1")
    except Exception as e:
        logging.error(f"Failed to read semantics file: {e}")
        return

    source_file = ATOMIC_COVERAGE_FILE if ATOMIC_COVERAGE_FILE.exists() else LEGACY_STATE_FILE
    if not source_file.exists():
        logging.warning("No coverage table found.")
        return

    table = []
    needs_update = False
    
    with open(source_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                cov_key = row.get("coverage_key", {})
                row_sem_ver = cov_key.get("semantics_version")
                
                if row_sem_ver != current_version:
                    row["status"] = "NEEDS_REBASE"
                    row["notes"] = f"Rebase required: {row_sem_ver} -> {current_version}"
                    needs_update = True
                
                table.append(row)
            except Exception:
                pass

    ATOMIC_COVERAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ATOMIC_COVERAGE_FILE, "w") as f:
        for row in table:
            f.write(json.dumps(row) + "\n")

    if needs_update:
        logging.info(f"Gated mismatched versions. Coverage table marked as NEEDS_REBASE.")
    else:
        logging.info("All coverage entries are semantically up-to-date.")

if __name__ == "__main__":
    main()
    exit(0)
