import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return None

def get_best_params_for_regime(run_dir: str, regime: str) -> Optional[Dict[str, Any]]:
    """
    API to retrieve the best parameters for a given regime from a backtest run.
    Regime: 'BULL', 'BEAR', 'NEUTRAL'
    
    Logic:
    1. Try optimizer_regime.json -> buckets -> regime -> topk[0]
    2. Fallback: optimizer.json -> best -> params
    3. Return None if neither exists.
    """
    run_path = Path(run_dir)
    reg_path = run_path / "optimizer_regime.json"
    opt_path = run_path / "optimizer.json"
    
    # 1. Try Regime-Aware
    reg_data = load_json(reg_path)
    if reg_data:
        buckets = reg_data.get("buckets", {})
        bucket = buckets.get(regime.upper(), {})
        topk = bucket.get("topk", [])
        if topk:
            return topk[0].get("params")
            
    # 2. Fallback to global best
    opt_data = load_json(opt_path)
    if opt_data:
        best = opt_data.get("best", {})
        return best.get("params")
        
    return None

def load_selection(run_dir: str) -> Optional[Dict[str, Any]]:
    """
    Load selection.json artifact.
    """
    path = Path(run_dir) / "selection.json"
    return load_json(path)

def get_current_selection(run_dir: str, respect_gate: bool = True) -> Dict[str, Any]:
    """
    Get the final trading decision and parameters.
    Returns: {
        "decision": "TRADE" | "HOLD",
        "symbol": str,
        "params": dict,
        "meta": dict,
        "source": "selection_artifact" | "fallback"
    }
    """
    # 1. Try Loading Artifact
    selection_data = load_selection(run_dir)
    
    if selection_data:
        decision = selection_data.get("decision", "HOLD")
        
        # Override if caller wants to ignore gate but artifact respected it? 
        # Actually artifact logic is final for that run context. 
        # But if we want to force read... 
        # For now, trust artifacts decision unless it's missing.
        
        selected = selection_data.get("selected") or {}
        return {
            "decision": decision,
            "symbol": selected.get("symbol"),
            "params": selected.get("params"),
            "meta": {
                "regime": selection_data.get("regime"),
                "gate": selection_data.get("gate", {}).get("overall"),
                "generated_at": selection_data.get("generated_at")
            },
            "source": "selection_artifact"
        }

    # 2. Fallback (Regime-Aware API)
    # If selection.json missing, we MUST default to HOLD for safety,
    # but return the best params for "what if" analysis.
    
    # Need to know regime to get params. 
    # Use regime_report if available, else NEUTRAL.
    run_path = Path(run_dir)
    reg_report = load_json(run_path / "regime_report.json")
    regime = "NEUTRAL"
    if reg_report:
        regime = reg_report.get("latest_regime", "NEUTRAL")
        
    best_params = get_best_params_for_regime(run_dir, regime)
    
    return {
        "decision": "HOLD", # Safety default
        "symbol": "BTCUSDT", # Default
        "params": best_params,
        "meta": {
            "regime": regime,
            "reason": "selection_artifact_missing"
        },
        "source": "fallback"
    }
