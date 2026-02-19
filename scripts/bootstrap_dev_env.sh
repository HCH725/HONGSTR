#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -e ".[dev]"

cat > .env.example <<'EOF'
BINANCE_FUTURES_TESTNET=1
BINANCE_TESTNET=0
BINANCE_API_KEY=
BINANCE_API_SECRET=
EOF

echo "Bootstrap complete."
echo "Use gate command: bash scripts/gate_all.sh"
echo ""
echo "Required env vars for exchange smoke:"
echo "- BINANCE_FUTURES_TESTNET"
echo "- BINANCE_TESTNET"
echo "- BINANCE_API_KEY"
echo "- BINANCE_API_SECRET"
echo ""
echo "Quick start (safe template):"
echo "cp .env.example .env"
echo "export \$(grep -v '^#' .env | xargs)"
