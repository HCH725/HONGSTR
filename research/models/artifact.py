import joblib
import json
import logging
from pathlib import Path

logger = logging.getLogger("research.models.artifact")

def save_model_artifact(model_obj, meta: dict, out_dir: str):
    """
    Saves a trained model (or dict of models) to disk along with strictly typed JSON metadata.
    
    Args:
        model_obj: Any joblib-serializable Python object (e.g. Scikit-Learn model or dict of models).
        meta: Dictionary containing feature_schema, label_spec, train_spec, data_fingerprint, etc.
        out_dir: The directory to write the model.pkl and model_meta.json to.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    pkl_path = out_path / "model.pkl"
    meta_path = out_path / "model_meta.json"
    
    # Save Model Weights
    joblib.dump(model_obj, pkl_path)
    logger.info(f"Saved model to {pkl_path}")
    
    # Save Metadata
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, default=str)
    logger.info(f"Saved model metadata to {meta_path}")
    
def load_model_artifact(artifact_dir: str):
    """
    Loads a model and its metadata from a given directory.
    
    Returns:
        model_obj, meta_dict
    """
    path = Path(artifact_dir)
    pkl_path = path / "model.pkl"
    meta_path = path / "model_meta.json"
    
    if not pkl_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"Missing model.pkl or model_meta.json in {artifact_dir}")
        
    model_obj = joblib.load(pkl_path)
    with open(meta_path, "r") as f:
        meta = json.load(f)
        
    return model_obj, meta
