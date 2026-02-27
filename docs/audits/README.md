# Audits Artifacts (Reference)

This folder stores generated audit artifacts that are attached in policy/report PRs.

- Regime threshold weekly calibration audits:
  - `regime_threshold_calibration_YYYYMMDD.md`
  - `regime_threshold_calibration_YYYYMMDD.json`

Generation entrypoint (report_only):

```bash
bash scripts/calibrate_regime_thresholds.sh --prepare-pr
```
