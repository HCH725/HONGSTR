import json
import logging
from pathlib import Path
import pandas as pd
from typing import Optional

from research.panel.spec import PanelSpec
from research.panel.gates import run_all_gates

logger = logging.getLogger("research.builder")

def build_panel(spec: PanelSpec, data_root: str = "data/derived") -> Optional[pd.DataFrame]:
    """
    Builds a multi-index (ts, symbol) DataFrame correctly aligned from existing derived JSONL.
    Only consumes existing artifacts, does not make API calls.
    """
    dfs = []
    root_path = Path(data_root)

    # Date filtering
    try:
        start_ts = pd.to_datetime(spec.start, utc=True)
    except Exception:
        start_ts = pd.Timestamp("2000-01-01", tz="UTC")

    end_ts_val = spec.end
    if end_ts_val.lower() == "now":
        end_ts = pd.Timestamp.now(tz="UTC")
    else:
        try:
            end_ts = pd.to_datetime(end_ts_val, utc=True)
        except Exception:
            end_ts = pd.Timestamp.now(tz="UTC")

    for symbol in spec.symbols:
        file_path = root_path / symbol / spec.freq / "klines.jsonl"
        if not file_path.exists():
            logger.warning(f"File not found: {file_path}. Skipping symbol {symbol}.")
            continue
            
        # Parse JSONL
        records = []
        with open(file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                    
        if not records:
            continue
            
        df = pd.DataFrame(records)
        df["symbol"] = symbol
        
        # Convert Open Time to proper datetime
        if "ts" in df.columns:
            df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
        else:
            logger.warning(f"No ts column found in {file_path}")
            continue
            
        # Filter by start and end
        df = df[(df["ts"] >= start_ts) & (df["ts"] <= end_ts)]
        
        # Cast core columns
        core_cols = ["open", "high", "low", "close", "volume"]
        for c in core_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        
        dfs.append(df)

    if not dfs:
        logger.warning("No data loaded successfully from the specified symbols.")
        return None

    # Concatenate all into one master panel
    panel = pd.concat(dfs, ignore_index=True)
    
    # Set unique index multi-index ['ts', 'symbol'] and sort
    panel.set_index(["ts", "symbol"], inplace=True)
    panel.sort_index(inplace=True)

    # Run strict gates, but only WARN on failure
    passed = run_all_gates(panel)
    if not passed:
        logger.warning("Panel built but failed one or more Quality Gates. (Exit 0 due to stability-first).")

    return panel
