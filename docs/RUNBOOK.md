# HONGSTR Operator Runbook

This guide covers daily operations and maintenance tasks for the HONGSTR system.

## Daily Operations SOP

1. **Sync Data**: Ensure historical price data is up to date.

    ```bash
    python3 scripts/aggregate_data.py
    ```

2. **Verify Health**: Run the automated health check script.

    ```bash
    bash scripts/daily_backtest_healthcheck.sh
    ```

3. **Monitor Orders**: Check order statuses and reconcile with the exchange.

    ```bash
    python3 scripts/order_reconcile.py
    ```

## Emergency Procedures

### Stopping Execution

To immediately halt all automated trading:

1. Revoke API Keys in the Binance Dashboard.
2. Terminate all `python3 scripts/execute_paper.py` processes.

### Cleaning Corrupt Data

If backtests result in `NaN` ratios:

1. Delete the relevant symbol directory in `data/parquet/`.
2. Re-run `scripts/ingest_historical.py`.

## Further Reading

For detailed command references, see [docs/handoff/03_workflows_runbook.md](file:///Users/hong/Projects/HONGSTR/docs/handoff/03_workflows_runbook.md).
