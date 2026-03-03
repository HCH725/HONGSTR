import json
import os
import time
from pathlib import Path

def generate_worker_acceptance_check(repo_root: Path) -> dict:
    worker_state_dir = repo_root / "_local/worker_state_workers"
    report_out_dir = repo_root / "reports/research/worker_acceptance"
    report_out_dir.mkdir(parents=True, exist_ok=True)
    out_json = report_out_dir / "worker_acceptance_latest.json"
    out_md = report_out_dir / "worker_acceptance_latest.md"

    response = {
        "status": "UNKNOWN",
        "workers": {},
        "details": []
    }

    if not worker_state_dir.exists() or not worker_state_dir.is_dir():
        response["status"] = "OK" # Graceful fallback if no workers configured yet
        response["details"].append("No remote worker inboxes found in _local/worker_state_workers. System is local-only.")
        _write_outputs(response, out_json, out_md)
        return response

    workers_found = 0
    now = time.time()
    all_ok = True

    for w_name in os.listdir(worker_state_dir):
        w_path = worker_state_dir / w_name
        if not w_path.is_dir():
            continue

        workers_found += 1
        w_data = {"heartbeat_present": False, "heartbeat_age_sec": None, "status": "UNKNOWN"}

        hb_path = w_path / "worker_heartbeat.json"
        if hb_path.exists():
            w_data["heartbeat_present"] = True
            mtime = hb_path.stat().st_mtime
            age = now - mtime
            w_data["heartbeat_age_sec"] = round(age, 1)

            if age > 7200: # 2 hours
                w_data["status"] = "WARN"
                response["details"].append(f"Worker {w_name} heartbeat is stale ({w_data['heartbeat_age_sec']}s old).")
                all_ok = False
            else:
                w_data["status"] = "OK"

            try:
                with open(hb_path, "r", encoding="utf-8") as f:
                    hb_json = json.load(f)
                    w_data["role"] = hb_json.get("role", "unknown")
            except Exception:
                pass
        else:
            w_data["status"] = "WARN"
            response["details"].append(f"Worker {w_name} missing heartbeat JSON.")
            all_ok = False

        response["workers"][w_name] = w_data

    if workers_found == 0:
        response["status"] = "OK"
        response["details"].append("Worker directory exists but is empty.")
    elif all_ok:
        response["status"] = "OK"
        response["details"].append(f"All {workers_found} connected workers are reporting functionally.")
    else:
        response["status"] = "WARN"

    _write_outputs(response, out_json, out_md)
    return response

def _write_outputs(response: dict, json_path: Path, md_path: Path):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)

    status_icon = "🟢" if response["status"] == "OK" else ("🟡" if response["status"] == "WARN" else "🔴")
    md = [
        f"## {status_icon} Worker Acceptance Report: {response['status']}",
        ""
    ]

    if not response.get("workers"):
        md.append("No active external workers connected.")
    else:
        md.append("### Linked Workers")
        for w_name, data in response["workers"].items():
            mark = "✅" if data["status"] == "OK" else "⚠️"
            age_str = f"{data.get('heartbeat_age_sec')} sec ago" if data.get("heartbeat_age_sec") is not None else "N/A"
            md.append(f"- {mark} **{w_name}** | Role: `{data.get('role', 'unknown')}` | Heartbeat: {age_str}")
    
    if response.get("details"):
        md.append("\n### Details")
        for d in response["details"]:
            md.append(f"- {d}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
