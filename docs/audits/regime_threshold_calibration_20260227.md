# Regime Threshold Calibration Audit

- generated_utc: 2026-02-27T16:35:58Z
- as_of_utc: 2026-02-27T16:35:58Z
- report_only: True

## Sample Window
- lookback_days: 90
- start_utc: 2026-02-20T02:04:32Z
- end_utc: 2026-02-26T21:04:35Z
- sample_count: 371

## Method
- metric: max_drawdown
- transform: severity=abs(min(0,mdd))
- warn_quantile: 0.9
- fail_quantile: 0.97
- no_lookahead_rule: sample.timestamp <= as_of_utc
- status: OK (calibrated_from_historical_distribution)

## Thresholds
- current WARN/FAIL: -0.08 / -0.14
- recommended WARN/FAIL: -0.187319 / -0.304028
- delta WARN/FAIL: -0.107319 / -0.164028

## Expected Impact (Historical)
- current FAIL ratio: 0.215633
- recommended FAIL ratio: 0.032345
- delta FAIL ratio: -0.183288

## Safety
- Semi-dynamic policy flow: calibration proposes candidate only.
- Active policy changes require reviewed PR merge.

## Rollback
```bash
git revert <merge_commit_sha>
```
