# Freshness 快照說明 (Snapshots)

## 門檻定義 (Thresholds)

Dashboard 與 `tg_cp` 使用一致的新鮮度門檻：

- **OK**: <= 12 小時 (Emerald)
- **WARN**: <= 48 小時 (Amber)
- **FAIL**: > 48 小時 (Rose) 或 檔案缺失 (N/A)

## 監控矩陣 (3×3 Matrix)

系統監控以下幣別與時框的資料完整性：

- **Symbols**: BTCUSDT, ETHUSDT, BNBUSDT
- **Timeframes**: 1m, 1h, 4h

## 運作機制

1. **快照產出**：由 `scripts/state_snapshots.py` 掃描 `data/derived/{sym}/{tf}/klines.jsonl` 並計算 `age_hours`。
2. **觸發方式**：`bash scripts/refresh_state.sh` 會呼叫上述腳本並將結果寫入 `data/state/freshness_table.json`。
3. **前端顯示**：Dashboard API 讀取該快照並在 A.Environment Control 區塊以 3×3 表格顯示。
