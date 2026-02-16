# HONGSTR Operations Guide

## Quickstart (Paper Mode)

Run the entire stack in **Paper Mode (B)**:

```bash
# 1. Setup Env (copy .env.example)
cp .env.example .env
# Edit .env with your keys

# 2. Run
python scripts/run_all_paper.py --seconds 60
```

## Environment Variables

Key variables in `.env`:

- `EXECUTION_MODE`: `B` (Paper) or `C` (Testnet).
- `BINANCE_API_KEY` / `SECRET`: Required for Testnet.
- `REALTIME_SYMBOLS`: Comma-separated (e.g., `BTCUSDT,ETHUSDT`).
- `SMOKE_TESTNET_ENABLED`: Enable for C13 live smoke.

## Logs & Artifacts

- **Logs**: `logs/run_all_paper.log` (Rotating)
- **State**: `data/state/`
  - `execution_result.jsonl`: Trade results.
  - `execution_intent.jsonl`: Logic decisions.
- **Signals**: `data/signals/YYYY-MM-DD/signals.jsonl`

## Common Issues

1. **No Signals**:
   - Check `data/signals/`.
   - Ensure `REALTIME_ENABLED=true`.
   - Check `logs/run_all_paper.log` for WebSocket errors.
   - The runner automatically injects a smoke signal if none appear >80% duration (Paper Mode only).

2. **Order Rejection**:
   - Check `execution_result.jsonl` for `REJECTED_RISK`.
   - Adjust `MAX_ORDER_NOTIONAL` in `.env`.

3. **Connectivity**:
   - Ensure VPN/Proxy if in restricted region.
   - `PING` errors in log.
