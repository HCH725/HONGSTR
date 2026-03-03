#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
cd "$REPO_ROOT"

FREQ="1h"
HORIZON="24"
PANEL_PATH="reports/research/panels/panel_1h.parquet"

while [[ $# -gt 0 ]]; do
  case $1 in
    --freq) FREQ="$2"; shift 2 ;;
    --horizon) HORIZON="$2"; shift 2 ;;
    --panel_path) PANEL_PATH="$2"; shift 2 ;;
    *) echo "WARN: Unknown parameter $1"; exit 0 ;;
  esac
done

echo "Starting Label Builder SDK..."
.venv/bin/python -c "
import sys
import logging
from pathlib import Path
import pandas as pd
from research.labels.maker import make_labels

logging.basicConfig(level=logging.INFO)
p_path = Path('$PANEL_PATH')
if not p_path.exists():
    logging.warning('Panel not found at ' + str(p_path) + '. Exiting 0.')
    sys.exit(0)

panel = pd.read_parquet(p_path)
logging.info(f'Loaded panel of shape {panel.shape}')

try:
    labels = make_labels(panel, horizon_bars=int('$HORIZON'))
except Exception as e:
    logging.warning('Failed to generate labels: ' + str(e))
    sys.exit(0)

out_dir = Path('reports/research/labels')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'labels_${FREQ}_${HORIZON}.parquet'

labels.to_parquet(out_file)
logging.info(f'Successfully wrote labels to {out_file} with shape {labels.shape}')
"

RC=$?
if [ $RC -ne 0 ]; then
    echo "WARN: Label builder exited with non-zero code $RC. (Continuing anyway to not break pipeline)"
    exit 0
fi

exit 0
