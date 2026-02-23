#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT"

FREQ="1h"
HORIZON="24"

while [[ $# -gt 0 ]]; do
  case $1 in
    --freq) FREQ="$2"; shift 2 ;;
    --horizon) HORIZON="$2"; shift 2 ;;
    *) echo "WARN: Unknown parameter $1"; exit 0 ;;
  esac
done

echo "Starting ML Artifact Builder..."
.venv/bin/python -c "
import sys
import logging
from datetime import datetime, timezone
import subprocess
from pathlib import Path
import pandas as pd
from sklearn.linear_model import LogisticRegression, Ridge

from research.models.baseline import split_time_based
from research.models.artifact import save_model_artifact

logging.basicConfig(level=logging.INFO)

ds_path = Path('reports/research/datasets/dataset_${FREQ}_${HORIZON}.parquet')
if not ds_path.exists():
    logging.warning(f'Dataset not found at {ds_path}. Run build_dataset first.')
    sys.exit(0)

try:
    dataset = pd.read_parquet(ds_path)
    label_cols = ['fwd_return', 'direction']
    feature_cols = [c for c in dataset.columns if c not in label_cols]
    
    df_is, df_oos = split_time_based(dataset)
    X_train = df_is[feature_cols]
    y_train_r = df_is['fwd_return']
    y_train_c = df_is['direction']
    
    # Train dict of models
    logging.info('Fitting Ridge Model (for y_hat)...')
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train_r)
    
    logging.info('Fitting Logistic Regression (for p_up)...')
    logreg = LogisticRegression(class_weight='balanced', max_iter=1000)
    logreg.fit(X_train, y_train_c)
    
    model_obj = {
        'ridge': ridge,
        'logreg': logreg
    }
    
    # Build Metadata
    # Attempt to grab git commit
    git_commit = 'unknown'
    try:
        git_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
    except Exception:
        pass
        
    if isinstance(dataset.index, pd.MultiIndex):
        ts_vals = dataset.index.get_level_values('ts')
    else:
        ts_vals = dataset.index
        
    meta = {
        'feature_schema': {col: str(dataset[col].dtype) for col in feature_cols},
        'label_spec': {
            'horizon': int('${HORIZON}'),
            'regression': 'fwd_return',
            'classification': 'direction (fwd_return > 0)'
        },
        'train_spec': {
            'is_split_logic': '<= 2024-12-31 23:59:59 UTC',
            'is_rows': len(df_is),
            'oos_rows': len(df_oos),
        },
        'data_fingerprint': {
            'rowcount': len(dataset),
            'earliest_utc': str(ts_vals.min()),
            'latest_utc': str(ts_vals.max()),
        },
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': git_commit
    }
    
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    out_dir = Path(f'reports/research/models/baseline_${FREQ}_${HORIZON}/{timestamp}')
    
    save_model_artifact(model_obj, meta, str(out_dir))
    
except Exception as e:
    logging.warning(f'Failed to build model artifact: {e}')
    sys.exit(0)
"

RC=$?
if [ $RC -ne 0 ]; then
    echo "WARN: Script exited with non-zero code $RC."
fi
exit 0
