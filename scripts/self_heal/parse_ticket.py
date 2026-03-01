#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        print("ERROR: empty stdin", file=sys.stderr)
        return 2
    try:
        obj: Dict[str, Any] = json.loads(raw)
    except Exception as e:
        print(f"ERROR: invalid JSON: {e}", file=sys.stderr)
        return 2
    for k in ["title", "allowed_paths", "problem", "expected", "must_run"]:
        if k not in obj:
            print(f"ERROR: missing key: {k}", file=sys.stderr)
            return 2
    if not isinstance(obj["allowed_paths"], list) or not all(isinstance(x, str) for x in obj["allowed_paths"]):
        print("ERROR: allowed_paths must be list[str]", file=sys.stderr)
        return 2
    print(json.dumps(obj, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
