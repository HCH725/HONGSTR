# Audits Artifacts (Reference)

This folder stores generated audit artifacts that are attached in policy/report PRs.

- Regime threshold weekly calibration audits:
  - `regime_threshold_calibration_YYYYMMDD.md`
  - `regime_threshold_calibration_YYYYMMDD.json`

Generation entrypoint (report_only candidate; no active policy change):

```bash
bash scripts/calibrate_regime_thresholds.sh --as-of-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Policy-PR materialization mode (writes active policy + docs/audits artifacts for review PR):

```bash
bash scripts/calibrate_regime_thresholds.sh --pr-mode --as-of-utc "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```
