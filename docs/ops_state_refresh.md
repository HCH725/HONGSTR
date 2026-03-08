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

- `system_health_latest.json` 是 **preferred consumer path**
- `daily_report_latest.json` 是 companion summary，不得重算 freshness / coverage
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
- tg_cp / dashboard 可以保留 fallback，但 fallback 只能在 canonical JSON 缺失時發生，不能變成平行 truth source

## 運作機制

1. **快照產出**：由 `scripts/state_snapshots.py` 掃描並計算時間差。若檔案缺失，會標註 `reason="missing_source"`，且 `is_usable=false`。
2. **觸發方式**：`bash scripts/refresh_state.sh`。
3. **Canonical gate**：`system_health_latest.json.components.data_quality_gate` 提供 Stage 1 最小可讀 gate contract；consumer 應只讀，不應自行重新推理缺漏/過舊語義。
4. **Canonical contract**：`reason / source / evidence` vocabulary 由 producer 在上述 JSON 中直接寫出，供 consumer 只讀。
5. **前端/TG 顯示**：Dashboard API 與 Telegram `/freshness` 指令均優先讀取此 JSON 快照，確保兩端顯示完全同步。

## Stage 2 Card A: canonical state writer boundary

State Plane 的 writer / orchestrator 邊界固定如下：

- designated writer: `scripts/state_snapshots.py`
- designated orchestrator: `scripts/refresh_state.sh`
- machine-checkable inventory + ownership mapping:
  - `scripts/state_writer_inventory.py`
- machine-checkable guardrail:
  - `python3 scripts/check_state_writer_boundary.py --strict`

Card A 規則：

- `scripts/state_snapshots.py` 是唯一允許寫 canonical `data/state/*` 的 non-test path
- `scripts/refresh_state.sh` 只負責呼叫 atomic producers 與 canonical writer，不得自己寫 canonical state
- canonical inventory 必須完整覆蓋 `state_snapshots.py` 實際寫出的 artifacts；inventory 漏列或 stale path 都應判 `FAIL`

目前 inventory 涵蓋的 canonical / governed outputs 包含：

- `system_health_latest.json`
- `daily_report_latest.json`
- `freshness_table.json`
- `coverage_matrix_latest.json`
- `coverage_table.jsonl`
- `coverage_latest.json`
- `coverage_summary.json`
- `strategy_pool_summary.json`
- `regime_monitor_latest.json`
- `regime_monitor_summary.json`
- `execution_mode.json`
- `services_heartbeat.json`
- `brake_health_latest.json`
- `watchdog_status_latest.json`
- `cost_sensitivity_matrix_latest.json`
- `data_catalog_latest.json`
- `data_catalog_changes_latest.json`
- `changes_latest.json`
- `okx_public_coverage_latest.json`
- `bitfinex_public_coverage_latest.json`
- `cmc_market_intel_coverage_latest.json`
- `strategy_dashboard_latest.json`
- `data/state/_history/data_catalog_prev.json`

Card A 不處理：

- `refresh_state` partial-failure publish semantics（Stage 2 / Card B）
- `/status` health-pack consumer fallback（Stage 2 / Card C）
- `/daily` final acceptance audit（Stage 2 / Card D）
