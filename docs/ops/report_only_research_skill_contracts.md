# Report-Only Research Skill Contracts

Reference only. These contracts document the stable JSON shape for the two read-only/report-only research credibility skills added in this change.

Guardrails:

- `src/hongstr/**` core semantics remain untouched.
- tg_cp integrations stay no-exec (`subprocess`, `os.system`, `Popen` are still forbidden).
- Runtime outputs live under `reports/research/**`.
- Classification is informational only; nothing here should block a pipeline.

## `data_lineage_fingerprint`

Primary output path:

- `reports/research/lineage/lineage_<UTC>.json`
- `reports/research/lineage/lineage_<UTC>.md`

Stable top-level JSON keys:

- `skill`
- `schema_version` = `lineage_fingerprint.v1`
- `status`
- `report_only`
- `actions`
- `constraints`
- `summary`
- `refresh_hint`
- `generated_utc`
- `code_ref`
- `fingerprint_sha256`
- `fingerprint_material`
- `daily_ssot_sources`
- `derived_data`
- `inputs`
- `findings`
- `evidence_refs`
- `missing_artifacts`
- `artifacts` (only when write mode is enabled)

`fingerprint_material` is the deterministic hash input. It intentionally excludes `generated_utc` and artifact file names so the same inputs yield the same `fingerprint_sha256`.

## `backtest_repro_gate`

Primary output path:

- `reports/research/repro_gate/repro_<UTC>.json`
- `reports/research/repro_gate/repro_<UTC>.md`

Stable top-level JSON keys:

- `skill`
- `schema_version` = `backtest_repro_gate.v1`
- `status`
- `report_only`
- `actions`
- `constraints`
- `summary`
- `refresh_hint`
- `generated_utc`
- `execution_mode`
- `runner_available`
- `baseline`
- `runs`
- `thresholds`
- `diff_stats`
- `classification`
- `inputs`
- `findings`
- `evidence_refs`
- `missing_artifacts`
- `artifacts` (only when write mode is enabled)

Classification rules:

- `OK`: all observed drift stays within configured thresholds and a live runner is available.
- `WARN`: degraded mode (`artifact_replay`), partial run errors, or drift exceeds the warn band but not the hard threshold.
- `FAIL`: at least one metric exceeds its hard drift threshold.

The default degraded mode is `artifact_replay`, which reuses the baseline summary snapshot when no live runner callable is available. This preserves a deterministic report shape without claiming a real rerun.
