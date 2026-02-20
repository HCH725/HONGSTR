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
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing streamlit..."
    python3 -m pip install streamlit pandas
fi

if ! python3 -c "import pandas" 2>/dev/null; then
    echo "Installing pandas..."
    python3 -m pip install pandas
fi

HOST_127="127.0.0.1"
PORT="8501"
echo "Starting HONGSTR Dashboard..."
echo "URL_127=http://${HOST_127}:${PORT}/"
echo "Press Ctrl+C to stop."

# Run Streamlit
streamlit run scripts/dashboard.py --server.address "$HOST_127" --server.port "$PORT" --server.headless true
