# Known Issues

A list of known limitations and current bugs in the HONGSTR system.

## 1. macOS urllib3 Warning

- **Issue**: `NotOpenSSLWarning`.
- **Status**: **Won't Fix**.
- **Reason**: Occurs on macOS with system Python and LibreSSL. Does not affect functionality.

## 2. Binance -1022 Troubleshooting

- **Issue**: Signature Verification Failed.
- **Status**: **Resolved** for current endpoints via URL-only pattern.
- **Guidance**: If adding a new Binance endpoint, ensure it follows the pattern in `src/hongstr/execution/binance_testnet.py`.

## 3. High Memory Usage on Full WF

- **Issue**: Running 20+ symbols in parallel across 5 windows can lead to OOM on small instances.
- **Mitigation**: Use the `--quick` flag or reduce the symbol list in `configs/windows.json`.

For deep technical dives into these issues, see [docs/handoff/06_known_issues.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/06_known_issues.md).
