#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: enforce_allowed_paths.py <ticket_json_path>", file=sys.stderr)
        return 2
    ticket_path = Path(sys.argv[1])
    ticket = json.loads(ticket_path.read_text(encoding="utf-8"))
    allowed = ticket.get("allowed_paths", [])
    allowed = [a if a.endswith("/") else a + "/" for a in allowed]
    out = subprocess.check_output(["git", "diff", "--name-only", "HEAD~1..HEAD"], text=True).strip().splitlines()
    bad = []
    for p in out:
        ok = any(p.startswith(a) for a in allowed)
        if not ok:
            bad.append(p)
    if bad:
        print("ERROR: files changed outside allowed_paths:", file=sys.stderr)
        for b in bad:
            print(b, file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
