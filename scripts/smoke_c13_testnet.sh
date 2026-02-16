#!/bin/bash
export PYTHONPATH=src
export EXECUTION_MODE=C
export SMOKE_TESTNET_ENABLED=true

# Load .env if present
if [ -f .env ]; then
    export $(cat .env | sed 's/#.*//g' | xargs)
fi

if [ -z "$BINANCE_API_KEY" ]; then
    echo "FAILURE: BINANCE_API_KEY not set. Mode C requires keys."
    exit 1
fi

echo "Running C13 Testnet Smoke..."
python scripts/run_testnet_smoke.py
