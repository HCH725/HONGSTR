#!/usr/bin/env python3
import json
import os
import time
from pathlib import Path

DEFAULT_MAX_AGE_SEC = 600


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def main() -> int:
    max_age = int(os.environ.get("TG_CP_MAX_AGE_SEC", str(DEFAULT_MAX_AGE_SEC)))
    state_dir = Path("data/state")
    hb = state_dir / "services_heartbeat.json"
    if not hb.exists():
        print("FAIL: missing data/state/services_heartbeat.json")
        return 2
    obj = _read_json(hb)
    if not obj:
        print("FAIL: unreadable services_heartbeat.json")
        return 2

    now = int(time.time())
    ts = obj.get("ts_utc") or obj.get("generated_utc") or obj.get("ts") or None
    if isinstance(ts, str) and ts.endswith("Z") and "T" in ts:
        try:
            import datetime as dt

            ts_epoch = int(dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
        except Exception:
            ts_epoch = None
    elif isinstance(ts, (int, float)):
        ts_epoch = int(ts)
    else:
        ts_epoch = None

    if ts_epoch is None:
        print("FAIL: heartbeat missing ts_utc/generated_utc")
        return 2

    age = now - ts_epoch
    if age > max_age:
        print(f"FAIL: heartbeat stale age_sec={age} > {max_age}")
        return 3

    print(f"OK: heartbeat age_sec={age}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
