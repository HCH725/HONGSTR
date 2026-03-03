import json
from pathlib import Path
from typing import Any

def get_freshness_report(repo_path: Path, env: str) -> dict[str, Any]:
    """
    Generate a data freshness watchdog report from SSOT sources.
    Source Priority:
    1. system_health_latest.json (components.freshness)
    2. freshness_table.json
    """
    state_dir = repo_path / "data/state"
    health_pack_path = state_dir / "system_health_latest.json"
    freshness_table_path = state_dir / "freshness_table.json"

    source_mode = "unknown"
    metrics = {
        "p50": None,
        "p95": None,
        "max_gap": None,
        "missing_pct": None,
        "ts_utc": None
    }
    status = "UNKNOWN"

    # Try Health Pack first
    if health_pack_path.exists():
        try:
            with open(health_pack_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                comp = data.get("components", {}).get("freshness", {})
                if comp:
                    source_mode = "system_health_latest"
                    status = comp.get("status", "UNKNOWN")
                    metrics["max_gap"] = comp.get("max_age_h")
                    metrics["ts_utc"] = data.get("generated_utc")
        except Exception:
            pass

    # Fallback to Freshness Table
    if source_mode == "unknown" and freshness_table_path.exists():
        try:
            with open(freshness_table_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                rows = data.get("rows", [])
                if rows:
                    source_mode = "ssot_fallback"
                    metrics["ts_utc"] = data.get("ts_utc")
                    
                    ages = [row["age_h"] for row in rows if "age_h" in row]
                    statuses = [row["status"] for row in rows if "status" in row]
                    
                    if ages:
                        metrics["max_gap"] = max(ages)
                    
                    if all(s == "OK" for s in statuses):
                        status = "OK"
                    elif any(s == "FAIL" for s in statuses):
                        status = "FAIL"
                    else:
                        status = "WARN"
        except Exception:
            pass

    # Build Markdown Summary
    sections = [
        "🐕 *Data Freshness Watchdog*",
        f"Status: {status}",
        f"Mode: {source_mode}",
        ""
    ]

    if source_mode == "unknown":
        sections.append("❌ No freshness data found. Please run `refresh_state.sh`.")
    else:
        sections.append(f"• *Max Gap:* {metrics['max_gap']}h" if metrics['max_gap'] is not None else "• *Max Gap:* Unknown")
        sections.append(f"• *P50 (Approx):* {metrics['p50']}" if metrics['p50'] is not None else "• *P50:* null (SSOT-only)")
        sections.append(f"• *P95 (Approx):* {metrics['p95']}" if metrics['p95'] is not None else "• *P95:* null (SSOT-only)")
        sections.append(f"• *Missing Pct:* {metrics['missing_pct']}%" if metrics['missing_pct'] is not None else "• *Missing:* null (SSOT-only)")
        
        if metrics["ts_utc"]:
            sections.append(f"\n_Generated: {metrics['ts_utc']}_")

    return {
        "status": status,
        "report_only": True,
        "markdown": "\n".join(sections),
        "data": {
            "source_mode": source_mode,
            "metrics": metrics,
            "env": env
        }
    }
