# Freshness 快照說明 (Snapshots)

## 門檻定義 (Thresholds)

`scripts/state_snapshots.py` 會依 profile 套用固定 freshness thresholds：

- `realtime`: `ok_h=0.1`, `warn_h=0.25`, `fail_h=1.0`
- `backtest`: `ok_h=26.0`, `warn_h=50.0`, `fail_h=72.0`

注意：freshness `status` 與 Data Quality Gate 的 `is_usable` 不是同一件事。

- freshness `status` 仍維持 SSOT snapshot 的 `OK / WARN / FAIL / UNKNOWN`
- Data Quality Gate 另外用 machine-checkable `is_usable` 表達能否放行給 consumer
- Stage 1 規則：`gap / stale / missing / unknown => is_usable=false`

## 監控矩陣 (3×3 Matrix)

系統定期產出 `data/state/freshness_table.json` 作為單一事實來源 (Single Source of Truth)：

- **來源**: 統一代入 `data/derived/{sym}/{tf}/klines.jsonl`。
- **欄位**: 包含 `age_h`, `status`, `source`, `reason`, `is_usable`, `unusable_reason`。
- **Symbols**: BTCUSDT, ETHUSDT, BNBUSDT
- **Timeframes**: 1m, 1h, 4h

另外，`data/state/coverage_matrix_latest.json` 的每列也會帶同樣的 machine-checkable gate 欄位：

- `is_usable`
- `unusable_reason`

consumer 若需要單一 gate 結論，應讀：

- `data/state/system_health_latest.json`
- path: `components.data_quality_gate`

## Stage 1 Card C: coverage / freshness SSOT contract

本卡固定的 canonical publication contract 僅限以下 JSON：

- `data/state/system_health_latest.json`
- `data/state/daily_report_latest.json`
- `data/state/freshness_table.json`
- `data/state/coverage_matrix_latest.json`

其中：

- `system_health_latest.json` 是 **canonical health-pack path**
- `system_health_latest.json` 僅承載 **SystemHealth**，不得混入 `RegimeSignal` companion payload
- `daily_report_latest.json` 是 companion summary；如需 `RegimeSignal` 等非 SystemHealth 摘要，應由此 companion path 讀取
- `freshness_table.json` 與 `coverage_matrix_latest.json` 是 row-level canonical sources

固定欄位語意如下：

- `status`: producer 寫出的 canonical status
- `reason`: canonical status reason；consumer 不得自行補字串
- `source`: canonical upstream path 或 producer-owned source path
- `evidence`: machine-checkable evidence object，至少包含 `type` / `ref` / `observed_ts_utc`

readiness / freshness / coverage 三者必須共用同一組 publication 規則：

- readiness: `system_health_latest.json`
  - `ssot_status`
  - `ssot_reason`
  - `ssot_source`
  - `ssot_evidence`
- freshness: `freshness_table.json`
  - `rows[].status`
  - `rows[].reason`
  - `rows[].source`
  - `rows[].evidence`
- coverage: `coverage_matrix_latest.json`
  - `rows[].status`
  - `rows[].reason`
  - `rows[].source`
  - `rows[].evidence`
- system-level component mirror:
  - `system_health_latest.json -> components.freshness`
  - `system_health_latest.json -> components.coverage_matrix`

consumer-read 規則：

- consumer 只讀上述 canonical JSON
- canonical JSON 存在時，不得改讀 log、ad-hoc fields、或自行二次推理 freshness / coverage verdict
- `/status` 與 web status route 必須先讀 `system_health_latest.json`
- `system_health_latest.json` 缺失、壞檔、或不可解析時，`/status` 與 web status route 只能 deterministic 回 `UNKNOWN + refresh_hint`
- consumer 不得在 health pack 缺失時，改用 component files 自行合成 top-level `OK / WARN / FAIL`

## 運作機制

1. **快照產出**：由 `scripts/state_snapshots.py` 掃描並計算時間差。若檔案缺失，會標註 `reason="missing_source"`，且 `is_usable=false`。
2. **觸發方式**：`bash scripts/refresh_state.sh`。
3. **Canonical gate**：`system_health_latest.json.components.data_quality_gate` 提供 Stage 1 最小可讀 gate contract；consumer 應只讀，不應自行重新推理缺漏/過舊語義。
4. **Canonical contract**：`reason / source / evidence` vocabulary 由 producer 在上述 JSON 中直接寫出，供 consumer 只讀。
5. **前端/TG 顯示**：Dashboard API 與 Telegram `/status` 僅以 `system_health_latest.json` 作為 top-level health source；若 health pack 不可讀，必須直接提示 `bash scripts/refresh_state.sh`。
