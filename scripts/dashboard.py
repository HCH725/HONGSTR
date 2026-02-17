import streamlit as st
import pandas as pd
import json
import os
import sys
import glob
import time
from pathlib import Path
from datetime import datetime
import textwrap

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

# Try importing RegimeLabeler
try:
    from hongstr.regime.baseline import RegimeLabeler
except ImportError:
    RegimeLabeler = None

# --- Config ---
st.set_page_config(
    page_title="HONGSTR Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Helpers ---
def load_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        return None

def get_file_mtime(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except FileNotFoundError:
        return None

def get_backtest_runs(base_dir, limit=50):
    # Find all summary.json files
    pattern = str(base_dir / "*" / "*" / "summary.json")
    files = glob.glob(pattern)
    runs = []
    for f in files:
        p = Path(f)
        run_id = p.parent.name
        date_str = p.parent.parent.name
        mtime = os.path.getmtime(f)
        runs.append({
            "path": p.parent,
            "display": f"{date_str} / {run_id}",
            "mtime": mtime
        })
    # Sort by mtime desc
    runs.sort(key=lambda x: x["mtime"], reverse=True)
    return runs[:limit]

def format_delta(dt):
    if not dt:
        return "N/A"
    diff = datetime.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds/60)}m ago"
    else:
        return f"{int(seconds/3600)}h ago"

def load_benchmark_data():
    path = PROJECT_ROOT / "reports" / "benchmark_latest.json"
    return load_json(path)

def safe_get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        else:
            return default
    return d

def fmt_pct(x):
    return f"{x:.2%}" if isinstance(x, (float, int)) else "N/A"

def fmt_float(x):
    return f"{x:.2f}" if isinstance(x, (float, int)) else "N/A"

def fmt_int(x):
    return f"{int(x)}" if isinstance(x, (float, int)) else "N/A"

# --- Sidebar ---
st.sidebar.title("HONGSTR Local")

# Refresh
auto_refresh = st.sidebar.checkbox("Auto Refresh (10s)", value=True)
if auto_refresh:
    time.sleep(1) # Small delay to avoid busy loop 
    st.empty() # Placeholder for refresh logic handled by rerun? 
    # Streamlit rerun is tricky in loops. Using valid method:
    # st.experimental_rerun() is deprecated.
    # We rely on user action or simple loop structure if supported, 
    # but standard is create a loop outside or use st.empty().
    # Actually, `st_autorefresh` component is common, but let's stick to standard.
    # Minimal approach: checks tick every interaction. 
    # For actual auto-refresh, we can use `st.rerun()` with a sleep, 
    # but that blocks interaction. 
    # Better: user manually refreshes or we accept it's "interactive".
    # User asked for "Auto refresh every 10s". 
    # We can use javascript hack or simple loop? 
    # Let's use `st_autorefresh` if available or just basic sleep loop implies blocking.
    # The requirement says "Auto refresh every 10s".
    # We will insert a sleep at the end and rerun ONLY if auto_refresh is True.
    pass

# Backtest Selection
data_dir = PROJECT_ROOT / "data"
backtest_dir = data_dir / "backtests"
runs = get_backtest_runs(backtest_dir)
run_options = {r["display"]: r for r in runs}

selected_run_display = st.sidebar.selectbox(
    "Selected Backtest Run",
    options=list(run_options.keys()) if run_options else ["No Runs Found"]
)

# Metrics Timeframe
metrics_tf = st.sidebar.selectbox("Metrics Timeframe", ["4h", "1h"], index=0)

# --- Mode Detection ---
def detect_execution_mode():
    """
    Detects execution mode based on priority:
    1. ENV VAR: HONGSTR_EXEC_MODE or EXECUTION_MODE
    2. STATE FILES: data/state/*.json, logs/*heartbeat*.json => LOCAL_SERVICES
    3. DEFAULT: LOCAL
    """
    # 1. Env Var
    for key in ["HONGSTR_EXEC_MODE", "EXECUTION_MODE"]:
        val = os.environ.get(key)
        if val:
            return val.upper()
            
    # Check .env file manually
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        try:
            with open(env_path) as f:
                for line in f:
                    if line.startswith("HONGSTR_EXEC_MODE=") or line.startswith("EXECUTION_MODE="):
                        return line.strip().split("=", 1)[1].upper()
        except: pass

    # 2. State Files (LOCAL_SERVICES detection)
    # Check for active service indicators
    data_dir = PROJECT_ROOT / "data"
    patterns = [
        str(data_dir / "state" / "*.json"),
        str(data_dir / "realtime" / "state" / "*.json"),
        str(PROJECT_ROOT / "logs" / "*heartbeat*.json"),
        str(PROJECT_ROOT / "logs" / "*state*.json")
    ]
    
    for pat in patterns:
        if glob.glob(pat):
            return "LOCAL_SERVICES"
            
    # 3. Default
    return "LOCAL"

# --- Panel A: Environment Control ---
st.header("A. Environment Control")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("Execution Mode")
    mode = detect_execution_mode()
    
    # Color coding
    color = "blue"
    if mode == "LOCAL_SERVICES": color = "green"
    elif mode in ["PAPER", "LIVE"]: color = "red"
    
    st.markdown(f"Mode: :{color}[**{mode}**]")
    
    # Services Heartbeats
    st.write("**Services Heartbeat**")
    state_dir = data_dir / "state"
    services = glob.glob(str(state_dir / "*.json"))
    if not services:
        st.caption("No service state files found.")
    for s in services:
        name = Path(s).stem
        mt = get_file_mtime(s)
        st.write(f"- {name}: {format_delta(mt)}")

with col2:
    st.subheader("Data Freshness (1m)")
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    for sym in symbols:
        p = data_dir / "derived" / sym / "1m" / "klines.jsonl"
        if not p.exists():
            # Try csv
            p = data_dir / "derived" / sym / "1m" / "klines.csv"
        
        if p.exists():
            mt = get_file_mtime(p)
            age = (datetime.now() - mt).total_seconds()
            color = "green" if age < 300 else "orange" if age < 3600 else "red"
            st.markdown(f"{sym}: :{color}[{format_delta(mt)}]")
        else:
            st.markdown(f"{sym}: :red[MISSING]")

with col3:
    st.subheader("System Info")
    # Disk Usage (Approx)
    # Just count files in data/backtests?
    num_runs = len(runs)
    st.metric("Total Backtests", num_runs)
    
    # Alerts Preview
    # Try logs/
    logs_dir = PROJECT_ROOT / "logs"
    # Find latest realtime log? or alert log?
    # User said "last N telegram alert logs optional"
    st.caption("Alerts: N/A (Local)")

st.divider()

# --- Panel B: HONG Detail ---
st.header("B. HONG Detail")

# 1. Regime
st.subheader("1. Regime (Fixed 4h)")
regime_path = data_dir / "state" / "regime.json"
regime_data = load_json(regime_path)
regime_label = "UNKNOWN"
regime_source = "N/A"

if regime_data and "regime" in regime_data:
    regime_label = regime_data["regime"]
    regime_source = "Artifact"
else:
    # Fallback compute
    if RegimeLabeler:
        # Load BTC 4h
        btc_4h = data_dir / "derived" / "BTCUSDT" / "4h" / "klines.jsonl"
        if btc_4h.exists():
            try:
                df = pd.read_json(btc_4h, lines=True)
                if not df.empty and 'close' in df.columns:
                    labeler = RegimeLabeler()
                    labels = labeler.label_regime(df)
                    regime_label = labels.iloc[-1]
                    regime_source = "Computed (Fallback)"
            except Exception as e:
                regime_label = f"Error ({e})"
        else:
            regime_label = "MISSING DATA"
    else:
        regime_label = "ImportError"

st.markdown(f"Current Regime: **{regime_label}** *(Source: {regime_source})*")

# 2. Selection
st.subheader("2. HONG Selection")
sel_path = data_dir / "selection" / "hong_selected.json"
sel_data = load_json(sel_path)

if sel_data:
    ts = sel_data.get("timestamp", "N/A")
    commit = sel_data.get("git_commit", "N/A")
    st.caption(f"Generated: {ts} | Commit: {commit}")
    
    # Render tables for Bull/Bear/Neutral
    s_cols = st.columns(3)
    for idx, regime_key in enumerate(["bull", "neutral", "bear"]):
        with s_cols[idx]:
            st.markdown(f"**{regime_key.upper()}**")
            items = sel_data.get(regime_key, [])
            if items:
                # Minimal table
                df_sel = pd.DataFrame(items)
                # Show name and params if possible
                st.dataframe(df_sel, use_container_width=True, hide_index=True)
            else:
                st.write("None")
else:
    st.warning(f"MISSING: {sel_path}")

# 3. Performance Table
st.subheader(f"3. Backtest Performance ({metrics_tf})")

if selected_run_display != "No Runs Found":
    run_info = run_options[selected_run_display]
    run_dir = run_info["path"]
    summary_path = run_dir / "summary.json"
    summary_data = load_json(summary_path)
    
    if summary_data:
        per_symbol = summary_data.get("per_symbol", {})
        rows = []
        target_syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        
        for sym in target_syms:
            key = f"{sym}_{metrics_tf}"
            if key in per_symbol:
                m = per_symbol[key]
                row = {
                    "Symbol": key,
                    "Ret": f"{m.get('total_return', 0):.2%}",
                    "MDD": f"{m.get('max_drawdown', 0):.2%}",
                    "Sharpe": f"{m.get('sharpe', 0):.2f}",
                    "Trades": m.get("trades_count", 0),
                    "WinRate": f"{m.get('win_rate', 0):.2%}",
                    "Exp": f"{m.get('exposure_time', 0):.2%}"
                }
                # Debug counts
                dbg = m.get("debug_counts") or m.get("debug")
                if dbg:
                    row["Signals"] = dbg.get("signal_emitted", 0)
                else:
                    row["Signals"] = "?"
                rows.append(row)
            else:
                rows.append({
                    "Symbol": key,
                    "Ret": "MISSING",
                    "MDD": "-", "Sharpe": "-", "Trades": "-", "WinRate": "-", "Exp": "-", "Signals": "-"
                })
        
        st.table(pd.DataFrame(rows))
        

        # 4. Equity Curve
        st.subheader("4. Equity Curve")
        eq_path = run_dir / "equity_curve.jsonl"
        if eq_path.exists():
            # Load and plot
            try:
                # Read jsonl
                df_eq = pd.read_json(eq_path, lines=True)
                if not df_eq.empty:
                    df_eq["ts"] = pd.to_datetime(df_eq["ts"])
                    st.line_chart(df_eq, x="ts", y="equity")
                else:
                    st.info("Equity curve empty.")
            except Exception as e:
                st.error(f"Error reading equity curve: {e}")
        else:
            st.info("No equity_curve.jsonl found.")

    else:
        st.error(f"Failed to load summary.json from {run_dir}")

    # --- Panel C: Benchmark (FULL vs SHORT) ---
    st.header("C. Benchmark (FULL vs SHORT)")
    bench_data = load_benchmark_data()
    
    if bench_data:
        # File info
        bench_path = PROJECT_ROOT / "reports" / "benchmark_latest.json"
        mt = get_file_mtime(bench_path)
        size = os.path.getsize(bench_path) / 1024
        st.caption(f"Updated: {format_delta(mt)} | Size: {size:.1f} KB")

        # Top Summary
        st.subheader("Top Summary")
        c1, c2 = st.columns(2)
        
        for idx, kind in enumerate(["FULL", "SHORT"]):
            with (c1 if idx==0 else c2):
                st.markdown(f"**{kind}**")
                top = safe_get(bench_data, kind, "top")
                if top:
                    st.write(f"Period: {top.get('start_ts', '')[:10]} -> {top.get('end_ts', '')[:10]}")
                    st.write(f"Return: {fmt_pct(top.get('total_return'))}")
                    st.write(f"MDD: {fmt_pct(top.get('max_drawdown'))}")
                    st.write(f"Sharpe: {fmt_float(top.get('sharpe'))}")
                    st.write(f"Trades: {fmt_int(top.get('trades_count'))}")
                    st.write(f"WinRate: {fmt_pct(top.get('win_rate'))}")
                else:
                    st.info("No data")

        # Per-Symbol (4h)
        st.subheader("Per-Symbol (4h)")
        
        # Merge logic
        # We want rows: BTCUSDT_4h, ETHUSDT_4h, BNBUSDT_4h
        # Cols: FULL_Ret, SHORT_Ret...
        
        symbols = ["BTCUSDT_4h", "ETHUSDT_4h", "BNBUSDT_4h"]
        rows = []
        for sym in symbols:
            row = {"Symbol": sym}
            for kind in ["FULL", "SHORT"]:
                d = safe_get(bench_data, kind, "per_symbol_4h", sym)
                if d:
                    for k_short, k_long in [("total_return", "Ret"), ("max_drawdown", "MDD"), ("sharpe", "Sharpe"), ("trades_count", "Trades"), ("win_rate", "Win"), ("signal_emitted", "Signals")]:
                        val = d.get(k_short)
                        if k_long in ["Ret", "MDD", "Win"]:
                            fmt_val = fmt_pct(val)
                        elif k_long in ["Sharpe"]:
                            fmt_val = fmt_float(val)
                        else:
                            fmt_val = fmt_int(val)
                        row[f"{kind}_{k_long}"] = fmt_val
                else:
                     for k_long in ["Ret", "MDD", "Sharpe", "Trades", "Win", "Signals"]:
                         row[f"{kind}_{k_long}"] = "N/A"
            rows.append(row)
            
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    else:
         st.info("No benchmark_latest.json yet. Run scripts/benchmark_suite.sh first.")

    # --- Panel D: Optimization ---
    st.header("D. Optimization")
    opt_path = run_dir / "optimizer.json"
    opt_data = load_json(opt_path)
    
    if opt_data:
        # Layout: Best Params | Best Portfolio Metrics
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Best Parameters")
            best = opt_data.get("best", {})
            params = best.get("params", {})
            if params:
                st.json(params)
            else:
                st.write("No params found.")
        
        with c2:
            st.subheader("Best Metrics (Portfolio)")
            metrics_port = best.get("metrics_portfolio", {})
            if metrics_port:
                # Format nicely
                disp_metrics = {k: f"{v:.4f}" if isinstance(v, (float)) else v for k,v in metrics_port.items()}
                st.json(disp_metrics)
            else:
                st.write("No portfolio metrics.")
        
        # Top K Table
        st.subheader("Top K Models")
        top_k = opt_data.get("top_k", [])
        if top_k:
            df_top = pd.DataFrame(top_k)
            st.dataframe(df_top, use_container_width=True)
        else:
            st.info("No top_k results recorded (Single run?).")

    else:
        st.warning("No optimization artifact for this run.")

else:
    st.info("Select a backtest run to see details.")

# Auto-refresh logic (crudely)
if auto_refresh:
    time.sleep(10)
    st.rerun()
