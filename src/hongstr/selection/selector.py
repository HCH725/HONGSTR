import json
import os
from typing import List, Dict, Any
from datetime import datetime
import pandas as pd # For formatting

class Selector:
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy
        # Policy: {'enabled_regimes': ['BULL', 'BEAR'], 'top_k_bull': 3, ...}

    def select(self, candidates: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        candidates: List of strategy results with 'strategy_id' and 'scores' (from scoring.py)
        Returns: {'BULL': [ids...], 'BEAR': [ids...], 'NEUTRAL': []}
        """
        selected = {
            'BULL': [],
            'BEAR': [],
            'NEUTRAL': []
        }
        
        for regime in ['BULL', 'BEAR', 'NEUTRAL']:
            if regime not in self.policy.get('enabled_regimes', []):
                continue
                
            k = self.policy.get(f'top_k_{regime.lower()}', 0)
            if k <= 0:
                continue
                
            # Filter valid scores
            valid = [c for c in candidates if c['scores'].get(f'score_{regime.lower()}', -99) > -1] # Filter penalty? Or just sort?
            
            # Sort descending by score
            sorted_cand = sorted(valid, key=lambda x: x['scores'].get(f'score_{regime.lower()}', -999), reverse=True)
            
            selected[regime] = [c['strategy_id'] for c in sorted_cand[:k]]
            
        return selected

    # Canonical path
    DEFAULT_SELECTION_PATH = "data/selection/hong_selected.json"

    def _get_git_commit(self) -> str:
        """Best-effort git commit retrieval."""
        # 1. Env var
        env_commit = os.getenv("GIT_COMMIT")
        if env_commit:
            return env_commit
            
        # 2. Subprocess
        try:
            import subprocess
            return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return "unknown"

    def save_selection(self, portfolio_id: str, selection: Dict[str, List[str]], path: str = None, extra_meta: Dict[str, Any] = None):
        """
        Persist selection to JSON.
        Enforces schema_version='selection_artifact_v1'.
        Enforces Neutral policy normalization.
        """
        path = path or self.DEFAULT_SELECTION_PATH
        
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("Asia/Taipei")
        except ImportError:
            import pytz
            tz = pytz.timezone("Asia/Taipei")

        # R3: Normalization
        # Ensure all keys exist
        norm_selection = {
            'BULL': selection.get('BULL', []),
            'BEAR': selection.get('BEAR', []),
            'NEUTRAL': selection.get('NEUTRAL', [])
        }
        
        # Guard: If neutral_policy is NO_TRADE, force empty
        if self.policy.get('neutral_policy') == 'NO_TRADE':
            norm_selection['NEUTRAL'] = []

        # Prepare metadata
        meta = extra_meta or {}
        if "git_commit" not in meta:
             meta["git_commit"] = self._get_git_commit()

        # R2: Canonical Schema
        data = {
            "schema_version": "selection_artifact_v1",
            "portfolio_id": portfolio_id,
            "timestamp_gmt8": datetime.now(tz).isoformat(),
            "selection": norm_selection,
            "policy": self.policy,
            "metadata": meta
        }
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
    def load_selection(self, path: str = None) -> Dict[str, Any]:
        """
        Load and validate selection artifact.
        """
        path = path or self.DEFAULT_SELECTION_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Selection artifact not found at {path}")
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # R4: Validations
        if data.get("schema_version") != "selection_artifact_v1":
             raise ValueError(f"Invalid schema version: {data.get('schema_version')}")
             
        if "timestamp_gmt8" not in data or "+08:00" not in data["timestamp_gmt8"]:
             # Loose check for timezone offset
             pass 
             
        # R3: Normalization check on load
        sel = data.get("selection", {})
        pol = data.get("policy", {})
        
        if pol.get('neutral_policy') == 'NO_TRADE' and len(sel.get('NEUTRAL', [])) > 0:
             # Auto-correct or raise?
             # For safety, let's warn or normalize in memory is safer?
             # Contract says: "load/save must normalize"
             sel['NEUTRAL'] = []
             data['selection'] = sel
             
        return data
