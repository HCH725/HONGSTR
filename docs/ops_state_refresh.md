# Freshness 快照說明 (Snapshots)

## 門檻定義 (Thresholds)

Dashboard 與 `tg_cp` 使用一致的新鮮度門檻：

- **OK**: <= 12 小時 (Emerald)
- **WARN**: <= 48 小時 (Amber)
- **FAIL**: > 48 小時 (Rose) 或 檔案缺失 (N/A)

## 監控矩陣 (3×3 Matrix)

系統定期產出 `data/state/freshness_table.json` 作為單一事實來源 (Single Source of Truth)：

- **來源**: 統一代入 `data/derived/{sym}/{tf}/klines.jsonl`。
- **欄位**: 包含 `age_h`, `status`, `source`, `reason`。
- **Symbols**: BTCUSDT, ETHUSDT, BNBUSDT
- **Timeframes**: 1m, 1h, 4h

## 運作機制

1. **快照產出**：由 `scripts/state_snapshots.py` 掃描並計算時間差。若檔案缺失，會標註 `reason="missing_source"`。
2. **觸發方式**：`bash scripts/refresh_state.sh`。
3. **前端/TG 顯示**：Dashboard API 與 Telegram `/freshness` 指令均優先讀取此 JSON 快照，確保兩端顯示完全同步。
