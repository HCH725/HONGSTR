
import json, os, pathlib, sys, glob, argparse

def get_latest_summary_path():
    # Try finding the latest summary.json in data/backtests
    files = glob.glob("data/backtests/*/*/summary.json")
    if not files:
        return None
    # Sort by mtime, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    return pathlib.Path(files[0])

# Parse Args
parser = argparse.ArgumentParser()
parser.add_argument("--dir", type=str, help="Explicit backtest directory to verify")
args = parser.parse_args()

summary_path = None

if args.dir:
    p = pathlib.Path(args.dir) / "summary.json"
    if p.exists():
        summary_path = p
    else:
        print(f"Error: summary.json not found in {args.dir}", file=sys.stderr)
        print("Directory contents:", file=sys.stderr)
        os.system(f"ls -la {args.dir} >&2")
        sys.exit(1)
else:
    # Legacy/Fallback Logic
    latest_dir = os.environ.get("LATEST_DIR")

    if latest_dir:
        p = pathlib.Path(latest_dir) / "summary.json"
        if p.exists():
            summary_path = p
        else:
            print(f"LATEST_DIR ({latest_dir}) has no summary.json yet, falling back to latest completed run...", file=sys.stderr)

    if not summary_path:
        summary_path = get_latest_summary_path()
        if summary_path and not latest_dir:
             pass # Normal auto-discovery
        elif summary_path:
             print(f"Using fallback summary: {summary_path}", file=sys.stderr)

if not summary_path:
    print("No completed backtest found (summary.json missing). Backtest may still be running.", file=sys.stderr)
    sys.exit(1)

print(f"Using summary: {summary_path}")
d = json.load(summary_path.open())

top_keys = ["run_id","timestamp","start_equity","end_equity","total_return","max_drawdown","sharpe","trades_count","win_rate","avg_trade_return","exposure_time","start_ts","end_ts"]
print("=== TOP ===")
print({k:d.get(k) for k in top_keys})

print("\n=== PER_SYMBOL (4h only) ===")
ps = d.get("per_symbol", {})
for k in sorted(ps.keys()):
    if not k.endswith("_4h"):
        continue
    v = ps[k]
    out = {kk:v.get(kk) for kk in ["total_return","max_drawdown","sharpe","trades_count","win_rate","exposure_time","start_ts","end_ts"]}
    # Handle both potential key names for debug
    if "debug" in v:
        out["debug_counts"] = v["debug"]
    elif "debug_counts" in v:
        out["debug_counts"] = v["debug_counts"]
    print(f"{k}: {out}")
