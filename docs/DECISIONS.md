# Decision Log

This document tracks significant design choices made during the HONGSTR project.

## AD-001: Sequential URL-Only Requests for Binance

- **Context**: Binance -1022 errors were recurring due to payload re-encoding.
- **Decision**: All authenticated POST requests must bypass the `data=` parameter and send everything via the pre-signed URL.
- **Rationale**: Prevents libraries from re-ordering or re-encoding fields after the HMAC signature has been generated.

## AD-002: Dynamic Gate-Threshold Mapping

- **Context**: Static Sharpe thresholds failed to account for regime differences.
- **Decision**: Thresholds are now loaded from `configs/gate_thresholds.json` and can be calibrated against walk-forward stability metrics.

## AD-003: Parquet for Trade Logs

- **Context**: JSON trade logs for high-frequency strategies became unwieldy.
- **Decision**: Standardized all backtest outputs to Parquet.
- **Benefits**: Faster loading for analysis scripts and significantly smaller file sizes.

For more rationales, see [docs/handoff/07_decisions_and_rationales.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/07_decisions_and_rationales.md).
