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

## 運作機制

1. **快照產出**：由 `scripts/state_snapshots.py` 掃描並計算時間差。若檔案缺失，會標註 `reason="missing_source"`，且 `is_usable=false`。
2. **觸發方式**：`bash scripts/refresh_state.sh`。
3. **Canonical gate**：`system_health_latest.json.components.data_quality_gate` 提供 Stage 1 最小可讀 gate contract；consumer 應只讀，不應自行重新推理缺漏/過舊語義。
4. **前端/TG 顯示**：Dashboard API 與 Telegram `/freshness` 指令均優先讀取此 JSON 快照，確保兩端顯示完全同步。
