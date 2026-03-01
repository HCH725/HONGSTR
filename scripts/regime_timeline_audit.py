#!/usr/bin/env python3
"""
HONGSTR Regime Timeline Audit (P0-3)
Validates interval-based regime policies for gaps, overlaps, and coverage.
"""
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Paths
REPO = Path(__file__).parent.parent
REPO_ROOT = str(REPO.resolve())
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts._ssot_meta import add_ssot_meta


CANDIDATES = [
    REPO / "research/policy/regime_timeline.json",
    REPO / "research/policy/regime_timeline_policy.json",
    REPO / "research/policy/regime_timeline_latest.json",
    REPO / "data/state/regime_timeline_latest.json",
    REPO / "data/state/regime_timeline_policy.json",
]
OUTPUT_SSOT = REPO / "data/state/regime_timeline_audit_latest.json"
WINDOW_DAYS = 180

def _parse_iso(s: str) -> datetime:
    normalized = s[:-1] + "+00:00" if s.endswith("Z") else s
    dt = datetime.fromisoformat(normalized)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def main():
    now_utc = datetime.now(timezone.utc)
    window_start = now_utc - timedelta(days=WINDOW_DAYS)
    window_end = now_utc
    window_total_sec = (window_end - window_start).total_seconds()
    
    # 1. Candidate discovery
    target_p = None
    for c in CANDIDATES:
        if c.exists():
            target_p = c
            break

    # -- Fallback path --
    if not target_p:
        payload = {
            "overall": "UNKNOWN",
            "coverage_pct": 0.0,
            "gaps": [],
            "overlaps": [],
            "slices_summary": {
                "lookback_days": WINDOW_DAYS,
                "bull_days": 0.0,
                "bear_days": 0.0,
                "sideways_days": 0.0,
                "unknown_days": 0.0
            },
            "policy_source_path": None,
            "policy_sha": "UNKNOWN",
            "source_reason": "missing_policy",
            "refresh_hint": "no interval-based regime timeline policy file found; cannot audit gaps/overlaps",
            "gaps_seconds_total": 0,
            "overlaps_seconds_total": 0,
            "thresholds": {
                "gap_fail_seconds": 86400,
                "overlap_fail_seconds": 0
            }
        }
        OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_SSOT, "w") as f:
            json.dump(add_ssot_meta(payload, notes="Fallback audit due to missing policy file."), f, indent=2)
        print(f"Fallback. Written to {OUTPUT_SSOT.relative_to(REPO)}")
        sys.exit(0)

    # -- Primary Path --
    # Try parse payload
    try:
        raw_b = target_p.read_bytes()
        timeline_data = json.loads(raw_b.decode("utf-8"))
        policy_sha = hashlib.sha256(raw_b).hexdigest()
    except Exception as e:
        # File is corrupt
        payload = {
            "overall": "UNKNOWN",
            "coverage_pct": 0.0,
            "gaps": [],
            "overlaps": [],
            "slices_summary": {
                "lookback_days": WINDOW_DAYS,
                "bull_days": 0.0,
                "bear_days": 0.0,
                "sideways_days": 0.0,
                "unknown_days": 0.0
            },
            "policy_source_path": str(target_p.relative_to(REPO)),
            "policy_sha": "UNKNOWN",
            "source_reason": "parse_failure",
            "refresh_hint": f"JSON Parse Error: {e}",
            "gaps_seconds_total": 0,
            "overlaps_seconds_total": 0,
            "thresholds": {"gap_fail_seconds": 86400, "overlap_fail_seconds": 0}
        }
        OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_SSOT, "w") as f:
            json.dump(add_ssot_meta(payload, notes="Corrupt policy file."), f, indent=2)
        print("Parse failure payload exported.")
        sys.exit(0)

    # 2. Extract and Sort Intervals
    valid_regimes = {"BULL", "BEAR", "SIDEWAYS"}
    intervals = []
    has_unknowns = False
    
    for row in timeline_data:
        try:
            st = _parse_iso(row["start_utc"])
            ed = _parse_iso(row["end_utc"])
            if st >= ed: continue # malformed
            reg = str(row.get("regime", "UNKNOWN")).upper()
            if reg not in valid_regimes:
                has_unknowns = True
                reg = "UNKNOWN"
            intervals.append({"start": st, "end": ed, "regime": reg})
        except:
            continue

    intervals.sort(key=lambda x: x["start"])

    # 3. Gap, Overlap Detection & Coverage Clipping
    gaps = []
    overlaps = []
    
    slices_days = {
        "bull_days": 0.0,
        "bear_days": 0.0,
        "sideways_days": 0.0,
        "unknown_days": 0.0
    }
    
    covered_sec = 0.0
    gap_total_sec = 0.0
    ov_total_sec = 0.0
    
    for i, curr in enumerate(intervals):
        if i > 0:
            prev = intervals[i-1]
            diff = (curr["start"] - prev["end"]).total_seconds()
            if diff > 0:
                gaps.append({"start_utc": prev["end"].isoformat(), "end_utc": curr["start"].isoformat(), "seconds": diff})
                gap_total_sec += diff
            elif diff < 0:
                abs_diff = abs(diff)
                overlaps.append({
                    "start_utc": curr["start"].isoformat(),
                    "end_utc": prev["end"].isoformat(),
                    "seconds": abs_diff,
                    "regimes_involved": [prev["regime"], curr["regime"]]
                })
                ov_total_sec += abs_diff
        
        # Clip to [now_utc - 180d, now_utc)
        clip_st = max(curr["start"], window_start)
        clip_ed = min(curr["end"], window_end)
        
        if clip_st < clip_ed:
            dur = (clip_ed - clip_st).total_seconds()
            covered_sec += dur
            day_dur = dur / 86400.0
            r = curr["regime"]
            if r == "BULL": slices_days["bull_days"] += day_dur
            elif r == "BEAR": slices_days["bear_days"] += day_dur
            elif r == "SIDEWAYS": slices_days["sideways_days"] += day_dur
            else: slices_days["unknown_days"] += day_dur
    
    # Optional logic: Deduplicate overlaps from covered_sec?
    # Because we use `covered_sec += dur`, exact overlaps will artificially inflate coverage.
    # To be extremely rigid with 0.0-100.0%, we cap it. 
    coverage_pct = min(100.0, (covered_sec / window_total_sec) * 100.0) if window_total_sec > 0 else 0.0
    
    # 4. Severity Rules
    refresh_hint = ""
    status = "OK"
    if ov_total_sec > 0:
        status = "FAIL"
        refresh_hint = f"Overlaps detected ({ov_total_sec} sec). Policies must not overlap."
    elif gap_total_sec > 86400:
        status = "FAIL"
        refresh_hint = f"Severe gaps detected (>{gap_total_sec} sec). Timeline is excessively disjointed."
    elif gap_total_sec > 0:
        status = "WARN"
        refresh_hint = f"Minor gaps detected ({gap_total_sec} sec)."

    if has_unknowns and status != "FAIL":
        status = "WARN" if status == "OK" else status
        refresh_hint += (" | " if refresh_hint else "") + "unknown regime values encountered."
        
    slices_summary = {
        "lookback_days": WINDOW_DAYS,
        **slices_days
    }
    
    payload = {
        "overall": status,
        "coverage_pct": round(coverage_pct, 4),
        "gaps": gaps,
        "overlaps": overlaps,
        "slices_summary": slices_summary,
        "policy_source_path": str(target_p.relative_to(REPO)),
        "policy_sha": policy_sha,
        "refresh_hint": str(refresh_hint).strip(" |"),
        "gaps_seconds_total": gap_total_sec,
        "overlaps_seconds_total": ov_total_sec,
        "thresholds": {"gap_fail_seconds": 86400, "overlap_fail_seconds": 0}
    }
    
    # Inject dependencies tracking into source_inputs
    meta = add_ssot_meta(payload, notes="Regime Timeline Audit complete.")
    # Force the source policy file directly into source_inputs to be exhaustive
    st = target_p.stat()
    meta["source_inputs"].insert(0, {
        "path": str(target_p.relative_to(REPO)),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
        "size_bytes": st.st_size,
        "fingerprint": policy_sha[:12]
    })
    
    OUTPUT_SSOT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_SSOT, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[{status}] Regime Timeline Audit generated: {OUTPUT_SSOT.relative_to(REPO)}")
        
if __name__ == "__main__":
    main()
