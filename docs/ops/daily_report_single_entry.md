# Daily Report Single Entry (/daily)

> PRIMARY ENTRYPOINT
>
> 每日對外只看 Telegram `/daily`。此文件只定義契約與使用方式，其他治理/稽核/runbook 文件皆為 Reference。

## 1) Canonical SSOT

- File: `data/state/daily_report_latest.json`
- Schema version: `daily_report.v1`
- Producer: `scripts/state_snapshots.py`
- Consumers: `_local/telegram_cp/tg_cp_server.py` (`/daily`), dashboard read-only views

## 2) `/daily` 固定輸出模板（不可換順序）

1. `SystemHealth`
2. `DataFreshness`
3. `Backtest`
4. `StrategyPool+Leaderboard`
5. `Governance(Overfit)`
6. `Guardrails`

每一段固定三行：

- `狀態: OK/WARN/FAIL/UNKNOWN`
- `白話: 一句給非技術合夥人的解讀`
- `下一步: 一句 SOP`

## 3) 術語名詞表 (Acronym Glossary)

旨在幫助合夥人理解 `/daily` 報告中的關鍵指標與術語。

| 縮寫 | 中文白話說明 | 為什麼重要 / 看到 WARN 或 FAIL 要做什麼 |
| :--- | :--- | :--- |
| **SSOT** | 單一真理來源 | **底層數據一致性**。若 FAIL，代表不同組件數據打架，應聯絡技術團隊檢查 `refresh_state.sh`。 |
| **System Health** | 系統整體健康狀況 | **整機運行狀態**。若 FAIL，系統將進入「唯讀」或「暫停」模式。 |
| **Freshness** | 數據新鮮度 | **實時數據延遲**。若延遲超過 5min (WARN/FAIL)，代表 ETL 任務可能中斷或網路異常。 |
| **Coverage** | 數據覆蓋率 | **歷史數據完整性**。回測必須在 100% 覆蓋下才具參考價值。 |
| **Brake** | 安全剎車 | **自動化防護機制**。若 FAIL，代表核心安全檢查未通過，應人工介入。 |
| **Regime Monitor** | 市場環境監測 | **辨識牛熊市趨勢**。輔助判斷當前策略是否與市場匹配。 |
| **Regime Signal** | 市場風險訊號 | **信號開倉准許**。若為 FAIL，代表市場波動或風險過高，**暫不進場**；此為安全機制，不代表系統故障。 |
| **DD / MDD** | 跌幅 / 最大回撤 | **風險承受上限**。若近期回撤（DD）接近歷史最大值（MDD），代表策略可能正在失效。 |
| **Sharpe** | 夏普比率 | **性價比指標**。數值越高代表承擔單位風險獲得的回報越高（通常 > 1.5 較優）。 |
| **OOS / IS** | 樣本外 / 樣本內 | **防止過度擬合**。IS 是拿來調參數的，OOS（樣本外）才是真實表現。若 OOS 比 IS 差太多，代表策略「作弊」只對以前有效。 |
| **WF (Walkforward)** | 步進驗證 | **動態模擬**。模仿人類「看一段、測一段」的真實決策過程，比固定回測更可信。 |
| **L1 / L2 / L3** | 三層滑價模型 | **真實交易成本**。L1 是理想狀態，L3（最嚴苛）考量了訂單簿衝擊，更接近實盤。 |
| **DCA** | 定期定額/倍數攤平 | **進場策略**。透過分批進場降低平均成本。 |

## 4) 區段欄位解釋

- `regime_slice`: 當前回測所屬的市場環境（如 bull, bear, sideways）。
- `regime_window_utc`: 該環境所定義的時間區間（格式固定 `[start,end)`，UTC，end-exclusive）。
- `slice_rationale`: 切片採用理由（包含正常套用或降級原因碼）。
- `fallback_reason`: 若無法匹配特定環境時的降級原因（通常降級為 `ALL` 全時段觀測）。
- `slice_comparison_key`: 比較鍵（`strategy_id|direction|variant|regime_slice`），同策略跨切片比較必須帶此維度，避免樣本混在一起。

## 5) 缺值規則（硬性）

- 指標缺值不得顯示 `0.00`
- 一律使用：`null + metrics_status=UNKNOWN + metrics_unavailable_reason`
- `/daily` 顯示為：`資料不足/UNKNOWN`

## 6) LLM 潤飾策略

- 預設先生成 deterministic fallback（固定模板）
- 若 reasoning client 可用，僅做文字潤飾
- 若 LLM 失敗或 timeout：`DAILY_REPORT_STATUS: WARN`，並回退 deterministic fallback

## 7) 需要深入時去哪看 (Reference only)

- [Repository Inventory](../inventory.md)
- [Telegram Operator Manual](telegram_operator_manual.md)
- [Daily Report Contract](daily_report_contract.md)
