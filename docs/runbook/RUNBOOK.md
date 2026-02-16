# HONGSTR RUNBOOK (Phase 0)

> **Operational Procedures**
> This document describes how to operate, debug, and recover the system.

## 1. System Startup

### C9 Signal Engine

To run the Signal Engine with multiple strategies (VWAP Supertrend, RSI Divergence, MACD Divergence) and Real-time Feeds:

```bash
# Ensure environment variables are set (see .env.example)
export REALTIME_SYMBOLS="BTCUSDT,ETHUSDT,BNBUSDT"
export STRATEGY_ENABLED=true

# Run the integrated script
python3 scripts/run_signal_strategies.py --seconds 0  # 0 for infinite run
```

### Smoke Tests

- C7 (Realtime): `python3 scripts/run_ws.py`
- C8 (Signal Engine): `scripts/smoke_c8.sh`
- C9 (Strategies): `scripts/smoke_c9.sh`

## 2. Emergency Procedures

(To be defined in C5)

## 3. Deployment

(To be defined in C5)

## 4. Troubleshooting

(To be defined in C5)
