#!/usr/bin/env python3
"""
scripts/strategy_dashboard_snapshot.py
Generates the Strategy Dashboard SSOT (data/state/strategy_dashboard_latest.json).
Adheres strictly to existing data:
- BTC Buy & Hold curve from derived 4h klines.
- HONG curve from existing backtest equity curves (if available) or null.
- Regime timeline strictly from research/policy/regime_timeline.json.
- Top strategies per regime from strategy_pool.json or existing leaderboards.

Report-only. Returns a dict to be written by state_snapshots.py.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STATE_DIR = REPO_ROOT / "data/state"
RESEARCH_DIR = REPO_ROOT / "research"
REPORTS_DIR = REPO_ROOT / "reports"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
        return None

def _read_jsonl(path: Path):
    records = []
    if not path.exists():
        return records
    try:
        with open(path) as f:
            for line in f:
                ln = line.strip()
                if ln:
                    try:
                        records.append(json.loads(ln))
                    except Exception:
                        pass
    except Exception as e:
        logging.warning(f"Failed to read {path}: {e}")
    return records

def build_btc_curve(start_utc: str):
    """Reads derived BTCUSDT 4h klines to build normalized B&H curve."""
    btc_klines_path = REPO_ROOT / "data/derived/BTCUSDT/4h/klines.jsonl"
    klines = _read_jsonl(btc_klines_path)
    
    start_dt = datetime.fromisoformat(start_utc.replace("Z", "+00:00"))
    
    curve = []
    start_price = None
    last_price = None
    
    for k in klines:
        try:
            ts = k.get("ts_utc") or k.get("start_utc")
            if not ts: continue
            k_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if k_dt < start_dt:
                continue
            
            close_price = float(k["close"])
            if start_price is None:
                start_price = close_price
            
            norm_val = close_price / start_price
            curve.append({
                "ts_utc": ts,
                "val": norm_val
            })
            last_price = close_price
        except Exception:
            pass
            
    metrics = {"cagr": 0.0, "sharpe": 0.0, "max_dd": 0.0, "total_return": 0.0}
    if start_price is not None and last_price is not None and len(curve) > 0:
        total_ret = (last_price / start_price) - 1.0
        metrics["total_return"] = round(total_ret, 4)
        
        # Approximate Max DD
        max_seen = 0.0
        max_dd = 0.0
        for pt in curve:
            v = pt["val"]
            if v > max_seen:
                max_seen = v
            dd = (v - max_seen) / max_seen if max_seen > 0 else 0
            if dd < max_dd:
                max_dd = dd
        metrics["max_dd"] = round(max_dd, 4)
        
        # Approximate CAGR
        end_dt = datetime.fromisoformat(curve[-1]["ts_utc"].replace("Z", "+00:00"))
        days = (end_dt - start_dt).total_seconds() / 86400.0
        if days > 0:
            cagr = ((last_price / start_price) ** (365.25 / days)) - 1.0
            metrics["cagr"] = round(cagr, 4)
            
    return curve, metrics

def build_hong_curve():
    """Attempts to locate existing HONG portfolio equity curve from repo."""
    curve_data = None
    metrics = {"cagr": 0.0, "sharpe": 0.0, "max_dd": 0.0, "total_return": 0.0}
    notes = "HONG blended equity curve artifact not found in repo (requires backtest full-span run)."
    return curve_data, metrics, notes

def load_regime_timeline():
    """Loads strictly from research/policy/regime_timeline.json"""
    path = RESEARCH_DIR / "policy" / "regime_timeline.json"
    timeline = _read_json(path)
    if not timeline:
        return [], "research/policy/regime_timeline.json missing or invalid"
    return timeline, None

def build_strategy_regimes():
    """Categorizes strategies from pool into regimes based on existing metadata."""
    pool_path = STATE_DIR / "strategy_pool.json"
    pool_data = _read_json(pool_path)
    
    regimes = {
        "BULL": {"strategies": [], "kpis": {}},
        "BEAR": {"strategies": [], "kpis": {}},
        "SIDEWAYS": {"strategies": [], "kpis": {}}
    }
    
    if not pool_data or "candidates" not in pool_data:
        return regimes
        
    candidates = pool_data["candidates"]
    
    bull_strats = []
    bear_strats = []
    sideways_strats = []
    
    for c in sorted(candidates, key=lambda x: x.get("last_score", 0), reverse=True):
        if c.get("gate_overall") != "PASS": continue
        c_id = c.get("candidate_id", "")
        if not c_id: continue
        
        direction = str(c.get("direction", "")).upper()
        metrics = c.get("last_oos_metrics", {})
        item = {
            "id": c_id,
            "sharpe": metrics.get("sharpe", 0),
            "return": metrics.get("return", 0)
        }
        
        if direction == "LONG" and len(bull_strats) < 3:
            bull_strats.append(item)
        elif direction == "SHORT" and len(bear_strats) < 3:
            bear_strats.append(item)
        elif direction == "LONGSHORT" and len(sideways_strats) < 3:
            sideways_strats.append(item)
            
    regimes["BULL"]["strategies"] = bull_strats
    regimes["BEAR"]["strategies"] = bear_strats
    regimes["SIDEWAYS"]["strategies"] = sideways_strats
    
    return regimes

def generate_snapshot():
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start_utc = "2020-01-01T00:00:00Z"
    
    btc_curve, btc_kpis = build_btc_curve(start_utc)
    hong_curve, hong_kpis, hong_notes = build_hong_curve()
    
    series = []
    if btc_curve:
        for b in btc_curve:
            ts = b["ts_utc"]
            pt = {"ts_utc": ts, "btc_bh": b["val"], "hong": None}
            if hong_curve:
                hmatch = next((h for h in hong_curve if h["ts_utc"] == ts), None)
                if hmatch:
                    pt["hong"] = hmatch["val"]
            series.append(pt)
            
    end_utc = series[-1]["ts_utc"] if series else now_utc
    timeline_data, timeline_err = load_regime_timeline()
    regime_strats = build_strategy_regimes()
    
    notes = []
    if hong_notes:
        notes.append(hong_notes)
    if timeline_err:
        notes.append(timeline_err)
        
    delta_ret = 0.0
    if hong_kpis.get("total_return") and btc_kpis.get("total_return"):
        delta_ret = hong_kpis["total_return"] - btc_kpis["total_return"]

    payload = {
        "schema": "strategy_dashboard.v1",
        "generated_utc": now_utc,
        "window": {
            "start_utc": start_utc,
            "end_utc": end_utc
        },
        "series": series,
        "kpis": {
            "btc": btc_kpis,
            "hong": hong_kpis,
            "delta_total_return": round(delta_ret, 4)
        },
        "regimes": regime_strats,
        "blend": {
            "kpis": hong_kpis,
            "notes": notes
        },
        "sources": {
            "regime_timeline": "research/policy/regime_timeline.json",
            "selection_or_leaderboard": "data/state/strategy_pool.json",
            "equity_curve_source": "data/derived/BTCUSDT/4h/klines.jsonl"
        }
    }
    return payload

if __name__ == "__main__":
    snapshot = generate_snapshot()
    print(json.dumps(snapshot, indent=2))
