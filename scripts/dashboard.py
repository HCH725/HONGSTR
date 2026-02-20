import glob
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

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
    initial_sidebar_state="expanded",
)


# --- Helpers ---
def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def get_file_mtime(path):
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except FileNotFoundError:
        return None


def get_backtest_runs(base_dir, limit=50):
    run_dirs = [p for p in base_dir.glob("*/*") if p.is_dir()]
    total_runs = len(run_dirs)

    # Find all summary.json files
    pattern = str(base_dir / "*" / "*" / "summary.json")
    files = glob.glob(pattern)
    runs = []
    for f in files:
        p = Path(f)
        run_id = p.parent.name
        date_str = p.parent.parent.name
        mtime = os.path.getmtime(f)
        runs.append(
            {"path": p.parent, "display": f"{date_str} / {run_id}", "mtime": mtime}
        )
    # Sort by mtime desc
    runs.sort(key=lambda x: x["mtime"], reverse=True)
    return runs[:limit], total_runs


def format_delta(dt):
    if not dt:
        return "N/A"
    diff = datetime.now() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return f"{int(seconds)}s ago"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m ago"
    else:
        return f"{int(seconds / 3600)}h ago"


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
    time.sleep(1)  # Small delay to avoid busy loop
    st.empty()  # Placeholder for refresh logic handled by rerun?
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
run_limit = st.sidebar.slider("Loaded Runs Limit", 50, 500, 50, 50)
runs, total_runs = get_backtest_runs(backtest_dir, limit=run_limit)
run_options = {r["display"]: r for r in runs}
st.sidebar.caption(
    f"Loaded: {len(runs)} (limit={run_limit}) | Total detected: {total_runs}"
)

selected_run_display = st.sidebar.selectbox(
    "Selected Backtest Run",
    options=list(run_options.keys()) if run_options else ["No Runs Found"],
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
                    if line.startswith("HONGSTR_EXEC_MODE=") or line.startswith(
                        "EXECUTION_MODE="
                    ):
                        return line.strip().split("=", 1)[1].upper()
        except:  # noqa: E722
            pass

    # 2. State Files (LOCAL_SERVICES detection)
    # Check for active service indicators
    data_dir = PROJECT_ROOT / "data"
    patterns = [
        str(data_dir / "state" / "*.json"),
        str(data_dir / "realtime" / "state" / "*.json"),
        str(PROJECT_ROOT / "logs" / "*heartbeat*.json"),
        str(PROJECT_ROOT / "logs" / "*state*.json"),
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
    if mode == "LOCAL_SERVICES":
        color = "green"
    elif mode in ["PAPER", "LIVE"]:
        color = "red"

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
    st.metric("Total Backtests", total_runs)
    st.caption(f"Loaded runs: {len(runs)} (limit={run_limit})")
    st.caption("Note: scripts/retention_cleanup.sh may keep only latest N runs.")

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
                if not df.empty and "close" in df.columns:
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
                    "Ret": fmt_pct(m.get("total_return")),
                    "MDD": fmt_pct(m.get("max_drawdown")),
                    "Sharpe": fmt_float(m.get("sharpe")),
                    "Trades": m.get("trades_count", 0),
                    "WinRate": fmt_pct(m.get("win_rate")),
                    "Exp": fmt_pct(m.get("exposure_time")),
                }
                # Debug counts
                dbg = m.get("debug_counts") or m.get("debug")
                if dbg:
                    row["Signals"] = dbg.get("signal_emitted", 0)
                else:
                    row["Signals"] = "?"
                rows.append(row)
            else:
                rows.append(
                    {
                        "Symbol": key,
                        "Ret": "MISSING",
                        "MDD": "-",
                        "Sharpe": "-",
                        "Trades": "-",
                        "WinRate": "-",
                        "Exp": "-",
                        "Signals": "-",
                    }
                )

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
            with c1 if idx == 0 else c2:
                st.markdown(f"**{kind}**")
                top = safe_get(bench_data, kind, "top")
                if top:
                    st.write(
                        f"Period: {top.get('start_ts', '')[:10]} -> {top.get('end_ts', '')[:10]}"  # noqa: E501
                    )
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
                    for k_short, k_long in [
                        ("total_return", "Ret"),
                        ("max_drawdown", "MDD"),
                        ("sharpe", "Sharpe"),
                        ("trades_count", "Trades"),
                        ("win_rate", "Win"),
                        ("signal_emitted", "Signals"),
                    ]:
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

    # --- Panel D: Regime Performance (Fixed 4h) ---
    st.header("D. Regime Performance (Fixed 4h)")
    regime_rep_path = run_dir / "regime_report.json"
    regime_rep = load_json(regime_rep_path)

    if regime_rep:
        # File info
        mt = get_file_mtime(regime_rep_path)
        st.caption(f"Artifact: regime_report.json | Generated: {format_delta(mt)}")

        buckets = regime_rep.get("buckets", {})

        # 3 Columns for Overall Metrics
        c1, c2, c3 = st.columns(3)
        for idx, label in enumerate(["BULL", "NEUTRAL", "BEAR"]):
            with c1 if idx == 0 else c2 if idx == 1 else c3:
                st.markdown(f"**{label}**")
                b = buckets.get(label, {})
                if b and b.get("trades_count", 0) > 0 or b.get("total_return", 0) != 0:
                    st.write(f"Return: {fmt_pct(b.get('total_return'))}")
                    st.write(f"MDD: {fmt_pct(b.get('max_drawdown'))}")
                    st.write(f"Sharpe: {fmt_float(b.get('sharpe'))}")
                    st.write(f"Trades: {fmt_int(b.get('trades_count'))}")
                    st.write(f"WinRate: {fmt_pct(b.get('win_rate'))}")
                else:
                    st.info("No activity in this regime.")

        # Per Symbol Table
        st.subheader("Per-Symbol Metrics")
        rows = []
        target_syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

        for sym in target_syms:
            row = {"Symbol": sym}
            for label in ["BULL", "NEUTRAL", "BEAR"]:
                sdata = safe_get(buckets, label, "per_symbol", sym)
                if sdata:
                    row[f"{label}_Ret"] = fmt_pct(sdata.get("total_return"))
                    row[f"{label}_Win"] = fmt_pct(sdata.get("win_rate"))
                    row[f"{label}_Trades"] = fmt_int(sdata.get("trades_count"))
                else:
                    row[f"{label}_Ret"] = "N/A"
                    row[f"{label}_Win"] = "N/A"
                    row[f"{label}_Trades"] = "0"
            rows.append(row)

        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    else:
        st.warning("No regime_report.json found for this run.")
        st.info("Tip: Run scripts/run_and_verify.sh to generate all artifacts.")

    # --- Panel E: Gate (Regime Quality) ---
    st.header("E. Gate (Regime Quality)")
    gate_path = run_dir / "gate.json"
    gate_data = load_json(gate_path)

    if gate_data:
        res = gate_data.get("results", {})
        overall = res.get("overall", {})
        is_pass = overall.get("pass", False)

        # Big Pass/Fail indicator
        if is_pass:
            st.success("Overall Result: PASS")
        else:
            st.error("Overall Result: FAIL")
            if overall.get("reasons"):
                st.write("**Reasons for Failure:**")
                for r in overall.get("reasons"):
                    st.write(f"- {r}")

        # Table breakdown
        st.subheader("Regime Breakdown")
        by_regime = res.get("by_regime", {})
        table_rows = []
        for reg in ["BULL", "NEUTRAL", "BEAR"]:
            rdata = by_regime.get(reg, {})
            table_rows.append(
                {
                    "Regime": reg,
                    "Sharpe": fmt_float(rdata.get("sharpe")),
                    "MDD": fmt_pct(rdata.get("max_mdd")),
                    "Trades": rdata.get("trades", 0),
                    "PASS": "✅" if rdata.get("pass") else "❌",
                    "Reasons": ", ".join(rdata.get("reasons", [])),
                }
            )
        st.dataframe(
            pd.DataFrame(table_rows), use_container_width=True, hide_index=True
        )

    else:
        st.warning("Gate: N/A (no gate.json for this run yet)")

    # --- Panel F: Benchmark (Latest) ---
    st.header("F. Benchmark (Latest)")
    bench_data = load_json(PROJECT_ROOT / "reports" / "benchmark_latest.json")

    if bench_data:
        # File info
        bench_path = PROJECT_ROOT / "reports" / "benchmark_latest.json"
        mt = get_file_mtime(bench_path)
        st.caption(f"Artifact: benchmark_latest.json | Updated: {format_delta(mt)}")

        # FULL vs SHORT Summary
        st.subheader("Benchmark Summary")
        c1, c2 = st.columns(2)
        for idx, kind in enumerate(["FULL", "SHORT"]):
            with c1 if idx == 0 else c2:
                st.markdown(f"### {kind}")
                d = bench_data.get(kind, {})
                top = d.get("top", {})
                gate = d.get("gate_overall", {})

                if top:
                    st.write(f"Return: {fmt_pct(top.get('total_return'))}")
                    st.write(f"MDD: {fmt_pct(top.get('max_drawdown'))}")
                    st.write(f"Sharpe: {fmt_float(top.get('sharpe'))}")
                    st.write(f"Trades: {fmt_int(top.get('trades_count'))}")

                    # Gate Status
                    gpass = gate.get("pass", False)
                    if gpass:
                        st.success("Gate: PASS")
                    else:
                        st.error("Gate: FAIL")
                else:
                    st.info(f"No {kind} data found.")

        # Per-Symbol Table
        st.subheader("Per-Symbol (4h) Comparison")
        target_syms = ["BTCUSDT_4h", "ETHUSDT_4h", "BNBUSDT_4h"]
        rows = []
        for sym in target_syms:
            row = {"Symbol": sym}
            for kind in ["FULL", "SHORT"]:
                sdata = safe_get(bench_data, kind, "per_symbol_4h", sym)
                if sdata:
                    row[f"{kind}_Ret"] = fmt_pct(sdata.get("total_return"))
                    row[f"{kind}_MDD"] = fmt_pct(sdata.get("max_drawdown"))
                    row[f"{kind}_Sharpe"] = fmt_float(sdata.get("sharpe"))
                else:
                    row[f"{kind}_Ret"] = "N/A"
                    row[f"{kind}_MDD"] = "N/A"
                    row[f"{kind}_Sharpe"] = "N/A"
            rows.append(row)
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No benchmark_latest.json. Run scripts/benchmark_suite.sh to generate.")

    # --- Panel G: Optimization (Regime-aware) ---
    st.header("G. Optimization (Regime-aware)")
    reg_opt_path = run_dir / "optimizer_regime.json"
    reg_opt_data = load_json(reg_opt_path)

    if reg_opt_data:
        buckets = reg_opt_data.get("buckets", {})
        tabs = st.tabs(["BULL", "BEAR", "NEUTRAL"])

        for i, reg in enumerate(["BULL", "BEAR", "NEUTRAL"]):
            with tabs[i]:
                bdata = buckets.get(reg, {})
                st.write(f"**Sample Bars:** {bdata.get('sample_bars', 0)}")

                if bdata.get("warnings"):
                    for w in bdata.get("warnings"):
                        st.warning(w)

                st.subheader(f"Top-K Candidates for {reg}")
                topk = bdata.get("topk", [])
                if topk:
                    # Flatten for dataframe
                    rows = []
                    for cand in topk:
                        row = {
                            "Score (Sharpe)": fmt_float(
                                cand.get("score", {}).get("sharpe")
                            )
                        }
                        row.update(cand.get("params", {}))
                        m = cand.get("metrics", {})
                        row.update(
                            {
                                "Ret": fmt_pct(m.get("total_return")),
                                "MDD": fmt_pct(m.get("max_drawdown")),
                                "Trades": m.get("trades_count"),
                            }
                        )
                        rows.append(row)
                    st.dataframe(
                        pd.DataFrame(rows), use_container_width=True, hide_index=True
                    )
                else:
                    st.info("No candidates for this regime.")
    else:
        st.warning("No optimizer_regime.json found.")
        st.info("Tip: Run scripts/run_and_verify.sh to generate.")

    # Fallback to old optimizer.json info if useful
    st.divider()
    st.subheader("Global Optimization (optimizer.json)")
    opt_path = run_dir / "optimizer.json"
    opt_data = load_json(opt_path)
    if opt_data:
        best = opt_data.get("best", {})
        st.json(best.get("params", {}))
    else:
        st.write("No global optimizer artifact.")

    # --- Panel H: Selection (Regime-driven) ---
    st.header("H. Selection (Regime-driven)")
    sel_path = run_dir / "selection.json"
    sel_data = load_json(sel_path)

    if sel_data:
        # Top Metrics
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)
        decision = sel_data.get("decision", "HOLD")

        with dcol1:
            st.metric("Regime", sel_data.get("regime", "N/A"))
        with dcol2:
            st.metric("Decision", decision)
        with dcol3:
            gate_res = sel_data.get("gate", {}).get("overall", "UNKNOWN")
            st.metric("Gate", gate_res)
        with dcol4:
            selected = sel_data.get("selected")
            sym = selected.get("symbol") if selected else "N/A"
            st.metric("Symbol", sym)

        if decision == "HOLD":
            warns = sel_data.get("reasons", [])
            if warns:
                st.warning(f"Reasons: {', '.join(warns)}")

        # Details
        st.subheader("Selected Parameters")
        if selected:
            st.json(selected.get("params", {}))

            st.subheader("Candidate Rank 1 Metrics")
            st.json(selected.get("score", {}))
        else:
            st.info("No selection made.")

    else:
        st.warning("No selection.json found.")
        st.code(
            f"python3 scripts/generate_selection_artifact.py --run_dir {run_dir}",
            language="bash",
        )

    # --- Panel I: Walk-Forward / Regime Dataset ---
    st.header("I. Walk-Forward / Regime Dataset")
    wf_path = PROJECT_ROOT / "reports" / "walkforward_latest.json"
    wf_data = load_json(wf_path)

    if wf_data:
        # Summary Metrics
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "Windows Completed",
                f"{wf_data.get('windows_completed', 0)} / {wf_data.get('windows_total', 0)}",  # noqa: E501
            )
        with c2:
            st.caption(f"Generated: {wf_data.get('generated_at')}")

        # Stability
        st.subheader("Stability Analysis (Sharpe)")
        stab = wf_data.get("stability", {})
        if stab:
            s_rows = []
            for regime, stats in stab.items():
                row = {
                    "Regime": regime,
                    "Count": stats.get("count"),
                    "Mean": fmt_float(stats.get("mean_sharpe")),
                    "Median": fmt_float(stats.get("median_sharpe")),
                    "Min": fmt_float(stats.get("min_sharpe")),
                    "Max": fmt_float(stats.get("max_sharpe")),
                }
                s_rows.append(row)
            st.dataframe(
                pd.DataFrame(s_rows), use_container_width=True, hide_index=True
            )
        else:
            st.info("No stability data (need >1 run per regime type)")

        # Windows Table
        st.subheader("Windows Performance")
        windows = wf_data.get("windows", [])
        if windows:
            w_df = pd.DataFrame(windows)
            # Select columns
            cols = [
                "name",
                "start",
                "end",
                "gate_overall",
                "selection_decision",
                "sharpe",
                "mdd",
                "total_return",
            ]
            # Rename for display
            w_df = w_df[cols].rename(
                columns={
                    "gate_overall": "Gate",
                    "selection_decision": "Decision",
                    "sharpe": "Sharpe",
                    "mdd": "MDD",
                    "total_return": "Return",
                }
            )

            # Format
            w_df["Sharpe"] = w_df["Sharpe"].map(fmt_float)
            w_df["MDD"] = w_df["MDD"].map(fmt_pct)
            w_df["Return"] = w_df["Return"].map(fmt_pct)

            st.dataframe(w_df, use_container_width=True, hide_index=True)
        else:
            st.info("No windows data found.")

    else:
        st.info("No walkforward_latest.json found.")
        st.warning("Run One-Liner to Generate:")
        st.code("bash scripts/walkforward_suite.sh --quick", language="bash")

else:
    st.info("Select a backtest run to see details.")

    # --- Panel J: Action Items & Remediation ---
    st.header("J. Action Items & Remediation")
    actions_path = PROJECT_ROOT / "reports" / "action_items_latest.json"
    actions_data = load_json(actions_path)

    if actions_data:
        # Header Info
        ts = actions_data.get("generated_at", "N/A")
        source = actions_data.get("source", {}).get("type", "UNKNOWN")
        st.caption(f"Generated: {ts} | Source: {source}")

        # Overall Status
        col1, col2 = st.columns(2)
        gate = actions_data.get("overall_gate", "UNKNOWN")
        decision = actions_data.get("decision", "UNKNOWN")

        with col1:
            if gate == "PASS":
                st.success(f"Overall Gate: {gate}")
            else:
                st.error(f"Overall Gate: {gate}")
        with col2:
            st.metric("Decision", decision)

        # Top Actions
        st.subheader("Top Recommended Actions")
        top_actions = actions_data.get("top_actions", [])

        if top_actions:
            for act in top_actions:
                with st.expander(f"{act['rank']}. {act['title']}", expanded=True):
                    st.markdown(f"**Why:** {act['why']}")
                    st.markdown("**Suggested Changes:**")
                    for c in act.get("changes", []):
                        st.markdown(f"- {c}")

                    st.markdown("**Run Command:**")
                    for cmd in act.get("commands", []):
                        st.code(cmd, language="bash")

                    st.markdown(f"**Verify:** {', '.join(act.get('verify', []))}")
        else:
            st.success("No critical action items. System is healthy.")

        # Failing Windows Table
        failing = actions_data.get("failing_windows", [])
        if failing:
            st.subheader("Failing Windows Details")
            f_rows = []
            for w in failing:
                f_rows.append(
                    {
                        "Window": w.get("name"),
                        "Regime": w.get("regime"),
                        "Gate": w.get("gate"),
                        "Sharpe": f"{w.get('sharpe', 0):.2f}"
                        if w.get("sharpe") is not None
                        else "-",
                        "MDD": f"{w.get('mdd', 0):.2%}"
                        if w.get("mdd") is not None
                        else "-",
                        "Trades": w.get("trades", "-"),
                        "Notes": w.get("notes", ""),
                    }
                )
            st.dataframe(
                pd.DataFrame(f_rows), use_container_width=True, hide_index=True
            )

    else:
        st.info("No action_items_latest.json found.")
        st.warning("Run One-Liner to Generate:")
        st.code("python3 scripts/generate_action_items.py", language="bash")

# Auto-refresh logic (crudely)
if auto_refresh:
    time.sleep(10)
    st.rerun()
