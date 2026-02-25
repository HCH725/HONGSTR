import subprocess
import os
import json
import pandas as pd
from pathlib import Path

out_md = Path("reports/research/ml/phase5_demo_run.md")

commands = [
    ("1. Build Features", ["bash", "scripts/build_features.sh", "--freq", "1h", "--symbols", "BTCUSDT ETHUSDT BNBUSDT", "--start", "2020-01-01", "--end", "now"]),
    ("2. Build Labels", ["bash", "scripts/build_labels.sh", "--freq", "1h", "--horizon", "24"]),
    ("3. Run ML Baseline", ["bash", "scripts/run_ml_baseline.sh", "--freq", "1h", "--horizon", "24"]),
    ("4. Build Model Artifact", ["bash", "scripts/build_model_artifact.sh", "--freq", "1h", "--horizon", "24"]),
    ("5. Build Signals", ["bash", "scripts/build_signals.sh", "--freq", "1h", "--horizon", "24"]),
    ("6. Run Backtest (Report Only)", [".venv/bin/python", "scripts/run_backtest.py", "--signal-parquet", "reports/research/signals/signal_1h_24.parquet", "--signal-policy", "report_only", "--symbols", "BTCUSDT", "--timeframes", "1h", "--start", OOS_START_DATE, "--end", "2025-02-01"])
]

with open(out_md, "w") as f:
    f.write("# Phase 5 E2E Demo Run\n\n")
    f.write("This document verifies the read-only signal injection flow, from feature generation to backtest evidence.\n\n")

    for title, cmd in commands:
        print(f"Running {title}...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        f.write(f"### {title}: RC={res.returncode}\n")
        f.write("```text\n")
        f.write(res.stdout)
        if res.stderr:
            f.write(res.stderr)
        f.write("```\n\n")

    f.write("### 7. Verification Checklist\n")

    # 1. Artifact existence
    f.write("#### 7.1 Artifact Files Existence\n")
    models_dir = Path("reports/research/models")
    model_found = False
    for root, dirs, files in os.walk(models_dir):
        if "model.pkl" in files and "model_meta.json" in files:
            model_found = True
            f.write(f"- [x] Model artifacts found in: `{root}`\n")
            break
    if not model_found:
        f.write("- [ ] **Model artifacts MISSING**\n")

    # 2. Signal Parquet properties
    sig_path = Path("reports/research/signals/signal_1h_24.parquet")
    f.write("\n#### 7.2 Signal Parquet Properties\n")
    if sig_path.exists():
        df = pd.read_parquet(sig_path)
        f.write(f"- [x] Parquet exists at `{sig_path}`\n")
        f.write(f"- [x] Row count: {len(df):,}\n")
        
        if isinstance(df.index, pd.MultiIndex) and list(df.index.names) == ["ts", "symbol"]:
            f.write("- [x] Index is `MultiIndex('ts', 'symbol')`\n")
        else:
            f.write(f"- [ ] Index is NOT MultiIndex(ts, symbol). It is: {df.index.names}\n")
            
        if df.index.is_monotonic_increasing:
            f.write("- [x] Index is monotonically increasing chronologically\n")
        else:
            f.write("- [ ] Index is NOT monotonically increasing\n")
            
        if df.index.is_unique:
            f.write("- [x] Index has no duplicate keys\n")
        else:
            f.write("- [ ] Index HAS duplicate keys\n")
    else:
        f.write("- [ ] **Signal Parquet MISSING**\n")
        
    # 3. Backtest Summary parsing
    f.write("\n#### 7.3 Backtest ML Evidence Injection\n")
    runs = sorted(list(Path("data/backtests").glob("*/*")))
    if runs:
        latest_run = runs[-1]
        summary_path = latest_run / "summary.json"
        if summary_path.exists():
            with open(summary_path) as sf:
                sum_data = json.load(sf)
                if "ml_evidence" in sum_data:
                    ev = sum_data["ml_evidence"]
                    f.write(f"- [x] `ml_evidence` key FOUND in `{summary_path}`\n")
                    f.write(f"  - Policy: `{ev.get('policy')}`\n")
                    f.write(f"  - Coverage rows: {ev.get('coverage_rows')}\n")
                    f.write(f"  - Score Mean: {ev.get('score_mean')}\n")
                else:
                    f.write("- [ ] `ml_evidence` key MISSING from summary.json\n")
        else:
            f.write(f"- [ ] Backtest summary missing at {summary_path}\n")
            f.write(f"- Checked: {latest_run}\n")
    else:
        f.write("- [ ] No backtest runs found in data/backtests\n")

print("Done generating phase5_demo_run.md")
