import logging
import pandas as pd
import hashlib
from pathlib import Path
from research.models.artifact import load_model_artifact

logger = logging.getLogger("research.signals.generator")

def generate_signals(features_parquet: Path, model_artifact_path: Path, out_path: Path) -> pd.DataFrame:
    """
    Consumes features and a saved model artifact to produce a signals dataframe.
    Maintains exact row-level index alignment.
    """
    if not features_parquet.exists():
        logger.error(f"Features file not found at {features_parquet}")
        return pd.DataFrame()
        
    models, meta = load_model_artifact(str(model_artifact_path))
    
    # Load Models
    ridge = models.get("ridge")
    logreg = models.get("logreg")
    
    if ridge is None or logreg is None:
        logger.error("Loaded model artifact does not contain 'ridge' and 'logreg'.")
        return pd.DataFrame()
        
    # Load Features
    features_df = pd.read_parquet(features_parquet)
    # Filter features based on schema exact ordering
    schema = meta.get("feature_schema", {})
    feature_cols = list(schema.keys())
    
    # Check if we have all needed features
    missing = [c for c in feature_cols if c not in features_df.columns]
    if missing:
        logger.error(f"Missing required features: {missing}")
        return pd.DataFrame()
        
    # Strictly isolate the features for inference
    X = features_df[feature_cols]
    
    # Fill NaN safely (usually at warmup heads)
    # We use 0 as neutral/mean proxy for simple linear models during warmup
    # Strictly, NaNs shouldn't easily occur beyond the warmup unless gap
    X_filled = X.fillna(0)
    
    # Inference
    y_hat = ridge.predict(X_filled)
    # predict_proba returns [prob_class_0, prob_class_1]
    p_up = logreg.predict_proba(X_filled)[:, 1]
    
    # Calculate fusion signal_score. 
    # Let's map p_up [0..1] to [-1..1]
    # Then just average it softly with a clipped version of y_hat just for demo score purposes
    p_up_centered = (p_up - 0.5) * 2.0
    
    # Quick standardizer for y_hat demo scale (assuming returns are small like 0.01)
    # We clip y_hat * 10 to give it a rough [-1, 1] bounds
    y_hat_clipped = pd.Series(y_hat * 10).clip(-1, 1).values
    
    signal_score = (p_up_centered * 0.7) + (y_hat_clipped * 0.3)
    
    # Construct DataFrame exact to features layout
    signals = pd.DataFrame({
        "p_up": p_up,
        "y_hat": y_hat,
        "signal_score": signal_score,
        "model_commit": meta.get("git_commit", "unknown")
    }, index=features_df.index)
    
    return signals

def save_signal_manifest(signals: pd.DataFrame, out_dir: Path, freq: str, horizon: int, model_artifact_path: str):
    """Saves the signal manifest JSON for tracking."""
    # Hash the saved parquet
    parquet_path = out_dir / f"signal_{freq}_{horizon}.parquet"
    if not parquet_path.exists():
        return
        
    file_hash = hashlib.sha256(parquet_path.read_bytes()).hexdigest()
    
    manifest_data = {
        "freq": freq,
        "horizon": horizon,
        "rowcount": len(signals),
        "hash": file_hash,
        "model_artifact": str(model_artifact_path)
    }
    
    import json
    mani_path = out_dir / "signal_manifest.json"
    with open(mani_path, "w") as f:
        json.dump(manifest_data, f, indent=2)
    logger.info(f"Saved signal manifest to {mani_path}")
