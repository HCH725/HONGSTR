import json
import os
from pathlib import Path

def generate_run_integrity_report(repo_root: Path) -> dict:
    brake_health_path = repo_root / "reports/state_atomic/brake_health_latest.json"
    report_out_dir = repo_root / "reports/research/run_integrity"
    report_out_dir.mkdir(parents=True, exist_ok=True)
    out_json = report_out_dir / "run_integrity_latest.json"
    out_md = report_out_dir / "run_integrity_latest.md"

    response = {
        "status": "UNKNOWN",
        "run_dir": None,
        "files_present": {},
        "regime_slice_found": False,
        "leaderboard_ok": False,
        "details": []
    }

    if not brake_health_path.exists():
        response["status"] = "WARN"
        response["details"].append("brake_health_latest.json not found, cannot locate latest run.")
        _write_outputs(response, out_json, out_md)
        return response

    try:
        with open(brake_health_path, "r", encoding="utf-8") as f:
            brake_data = json.load(f)
    except Exception as e:
        response["status"] = "FAIL"
        response["details"].append(f"Failed to parse brake_health_latest.json: {str(e)}")
        _write_outputs(response, out_json, out_md)
        return response

    run_dir_str = None
    for res in brake_data.get("results", []):
        if res.get("item") == "Backtest summary.json":
            path_str = res.get("path", "")
            if path_str:
                run_dir_str = os.path.dirname(path_str)
            break

    if not run_dir_str:
        response["status"] = "WARN"
        response["details"].append("Could not find latest run directory from brake_health.")
        _write_outputs(response, out_json, out_md)
        return response

    response["run_dir"] = run_dir_str
    run_path = repo_root / run_dir_str

    if not run_path.exists():
        response["status"] = "FAIL"
        response["details"].append(f"Run dir does not exist locally: {run_dir_str}")
        _write_outputs(response, out_json, out_md)
        return response

    # Check files
    for fname in ["summary.json", "selection.json", "gate.json", "leaderboard.json"]:
        fpath = run_path / fname
        present = fpath.exists()
        response["files_present"][fname] = present
        if present and fname == "summary.json":
            try:
                with open(fpath, "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                    metadata = sdata.get("metadata", {})
                    if "regime_slice" in metadata or "regime_window_utc" in metadata:
                        response["regime_slice_found"] = True
            except Exception:
                pass
        if present and fname == "leaderboard.json":
            try:
                with open(fpath, "r", encoding="utf-8") as lf:
                    ldata = json.load(lf)
                    if isinstance(ldata, list) and len(ldata) > 0:
                        response["leaderboard_ok"] = True
            except Exception:
                pass

    missing = [k for k, v in response["files_present"].items() if not v]
    if missing:
        response["status"] = "WARN"
        response["details"].append(f"Missing files: {', '.join(missing)}")
    else:
        if not response["regime_slice_found"]:
            response["status"] = "WARN"
            response["details"].append("regime_slice metadata not found in summary.json")
        elif not response["leaderboard_ok"]:
            response["status"] = "WARN"
            response["details"].append("leaderboard.json is empty or malformed")
        else:
            response["status"] = "OK"
            response["details"].append("Run integrity verified successfully.")

    _write_outputs(response, out_json, out_md)
    return response

def _write_outputs(response: dict, json_path: Path, md_path: Path):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)

    status_icon = "🟢" if response["status"] == "OK" else ("🟡" if response["status"] == "WARN" else "🔴")
    md = [
        f"## {status_icon} Run Integrity Report: {response['status']}",
        f"**Run Dir:** `{response.get('run_dir', 'N/A')}`",
        "",
        "### Artifacts"
    ]
    for file, present in response.get("files_present", {}).items():
        mark = "✅" if present else "❌"
        md.append(f"- {mark} `{file}`")

    md.append("")
    md.append("### Semantics Check")
    md.append(f"- Regime Slice Found: {'Yes' if response.get('regime_slice_found') else 'No'}")
    md.append(f"- Leaderboard Valid: {'Yes' if response.get('leaderboard_ok') else 'No'}")

    if response.get("details"):
        md.append("\n### Details")
        for d in response["details"]:
            md.append(f"- {d}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
