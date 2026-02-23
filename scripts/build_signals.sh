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

export FREQ_ENV="${FREQ}"
export HORIZON_ENV="${HORIZON}"

echo "Starting Feature Inference SDK..."
.venv/bin/python -c "
import sys
import os
import logging
from pathlib import Path
from research.signals.generator import generate_signals, save_signal_manifest

logging.basicConfig(level=logging.INFO)

freq = os.environ.get('FREQ_ENV', '1h')
horizon = os.environ.get('HORIZON_ENV', '24')

features_dir = Path('reports/research/features')
features_path = features_dir / f'features_{freq}.parquet'

if not features_path.exists():
    logging.warning(f'Features missing at {features_path}. Run build_features.')
    sys.exit(0)

# Resolve latest model recursively
model_base = Path('reports/research/models') / f'baseline_{freq}_{horizon}'
if not model_base.exists():
    logging.warning(f'Model directory not found at {model_base}. Build model first.')
    sys.exit(0)
    
# Grab latest subfolder
subdirs = sorted([d for d in model_base.iterdir() if d.is_dir()])
if not subdirs:
    logging.warning(f'No model artifacts inside {model_base}')
    sys.exit(0)
    
latest_model_path = subdirs[-1]
out_dir = Path('reports/research/signals')
out_dir.mkdir(parents=True, exist_ok=True)

out_parquet = out_dir / f'signal_{freq}_{horizon}.parquet'

logging.info(f'Generating signals using model artifact {latest_model_path}...')
try:
    signals = generate_signals(features_path, latest_model_path, out_parquet)
    if len(signals) == 0:
        logging.warning('Signal generation resulted in empty output.')
        sys.exit(0)
        
    signals.to_parquet(out_parquet)
    logging.info(f'Saved signals to {out_parquet}')
    
    save_signal_manifest(signals, out_dir, freq, int(horizon), str(latest_model_path))
    
except Exception as e:
    logging.warning(f'Failed to generate signals: {e}')
    # Exit gracefully
    sys.exit(0)
"

RC=$?
if [ $RC -ne 0 ]; then
    echo "WARN: Signal generator exited with code $RC."
fi
exit 0
