#!/bin/bash
set -euo pipefail

# HONGSTR Dashboard Launcher

# Ensure we are in repo root
if [ ! -d ".venv" ]; then
    echo "Error: .venv not found. Please run 'uv venv' or ensure you are in the repo root."
    exit 1
fi

source .venv/bin/activate

# Check for dependencies
if ! python -c "import streamlit" 2>/dev/null; then
    echo "Installing streamlit..."
    pip install streamlit pandas
fi

if ! python -c "import pandas" 2>/dev/null; then
    echo "Installing pandas..."
    pip install pandas
fi

echo "Starting HONGSTR Dashboard..."
echo "Press Ctrl+C to stop."

# Run Streamlit
streamlit run scripts/dashboard.py
