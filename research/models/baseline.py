import json
import logging
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, precision_score, recall_score, mean_absolute_error

logger = logging.getLogger("research.models.baseline")

def split_time_based(dataset: pd.DataFrame, is_end="2024-12-31"):
    """Splits dataset strictly on time (IS vs OOS)."""
    # Assuming MultiIndex (ts, symbol) or ts in index level 0
    is_end_ts = pd.to_datetime(is_end, utc=True)
    if isinstance(dataset.index, pd.MultiIndex):
        ts_values = dataset.index.get_level_values(0)
    else:
        ts_values = dataset.index
        
    is_mask = ts_values <= (pd.to_datetime("2024-12-31 23:59:59", utc=True))

    df_is = dataset[is_mask]
    df_oos = dataset[~is_mask]
    return df_is, df_oos

def train_and_eval_classification(X_train, y_train, X_test, y_test):
    if len(X_test) == 0:
        return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0}
    model = LogisticRegression(class_weight="balanced", max_iter=1000)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    
    acc = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec = recall_score(y_test, preds, zero_division=0)
    
    return {
        "accuracy": acc,
        "precision": prec,
        "recall": rec
    }

def train_and_eval_regression(X_train, y_train, X_test, y_test):
    if len(X_test) == 0:
        return {"mae": 0.0, "correlation": 0.0, "directional_hit_rate": 0.0}
    model = Ridge(alpha=1.0)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    
    mae = mean_absolute_error(y_test, preds)
    # Correlation fallback if std is zero
    if np.std(preds) == 0 or np.std(y_test) == 0:
        corr = 0.0
    else:
        corr = np.corrcoef(y_test, preds)[0, 1]
        
    directional_hit_map = (np.sign(preds) == np.sign(y_test))
    hit_rate = directional_hit_map.mean()

    return {
        "mae": mae,
        "correlation": float(corr),
        "directional_hit_rate": float(hit_rate)
    }

def run_walkforward(df_oos, feature_cols, target_col, is_classification, n_folds=4):
    """Walkforward evaluation inside the OOS period using chronological splits."""
    if len(df_oos) < n_folds * 2:
        return []
        
    # Sort chronologically
    df_oos_sorted = df_oos.sort_index(level=0)
    
    fold_size = len(df_oos_sorted) // n_folds
    results = []
    
    # We expand the IS window inside the OOS set and predict the next chunk
    # e.g., train on Fold 1, predict Fold 2. Train F1+F2, predict F3.
    for i in range(1, n_folds):
        train_end_idx = i * fold_size
        test_end_idx = (i + 1) * fold_size
        
        train_chunk = df_oos_sorted.iloc[:train_end_idx]
        test_chunk = df_oos_sorted.iloc[train_end_idx:test_end_idx]
        
        X_tr, y_tr = train_chunk[feature_cols], train_chunk[target_col]
        X_te, y_te = test_chunk[feature_cols], test_chunk[target_col]
        
        if is_classification:
            res = train_and_eval_classification(X_tr, y_tr, X_te, y_te)
        else:
            res = train_and_eval_regression(X_tr, y_tr, X_te, y_te)
            
        res["fold"] = i
        results.append(res)
        
    return results

def run_baseline_suite(dataset: pd.DataFrame):
    """Executes the full suite including general IS/OOS split and Walkforward OOS."""
    # Find features vs labels
    label_cols = ["fwd_return", "direction"]
    feature_cols = [c for c in dataset.columns if c not in label_cols]
    
    if len(feature_cols) == 0 or "fwd_return" not in dataset.columns:
        logger.error("Dataset lacks required feature/label columns for baseline suite.")
        return {}

    df_is, df_oos = split_time_based(dataset)
    
    X_tr, y_tr_r, y_tr_c = df_is[feature_cols], df_is["fwd_return"], df_is["direction"]
    X_te, y_te_r, y_te_c = df_oos[feature_cols], df_oos["fwd_return"], df_oos["direction"]
    
    logger.info(f"Training Baseline. IS size: {len(df_is)}, OOS size: {len(df_oos)}")
    
    out = {
        "metadata": {
            "features_count": len(feature_cols),
            "is_rows": len(df_is),
            "oos_rows": len(df_oos),
        },
        "fixed_classification": train_and_eval_classification(X_tr, y_tr_c, X_te, y_te_c),
        "fixed_regression": train_and_eval_regression(X_tr, y_tr_r, X_te, y_te_r),
        "wf_classification": run_walkforward(df_oos, feature_cols, "direction", True),
        "wf_regression": run_walkforward(df_oos, feature_cols, "fwd_return", False),
    }
    
    return out
