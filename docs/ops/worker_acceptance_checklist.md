# Worker Acceptance Checklist (DoD)

> **PRIMARY ENTRYPOINT**
> 本文為 HONGSTR Worker（營運自動化）上線時的驗收標準（Definition of Done）。
> 術語縮寫定義請參考：[Daily Report Single Entry](daily_report_single_entry.md)

---

## A. 系統可用性 (System Availability)

確保基礎設施能長時間穩定運作且在異常時可優雅降級。

| 檢查項目 | PASS 條件 | FAIL 時 SOP |
| :--- | :--- | :--- |
| **運作時長** | 系統至少能順利連續運行 24–48 小時不崩潰。 | 檢查日誌，修復 memory leak 或死鎖問題。 |
| **資源上限** | CPU / Memory 佔用率必須保持在 80% 以下。 | 擴充硬體資源或優化耗能流程。 |
| **降載能力** | 遇到大流量或突發事件時不當機，可暫停非緊急任務排程。 | 審查 QoS 與 Rate Limiting 設定。 |
| **災難恢復** | 進程崩潰或被強制關閉後，可透過重啟自動恢復。 | 修補初始化流程，確保狀態具備冪等性 (Idempotent)。 |

## B. 資料可用性 (Data Availability)

確保底層數據流與回測核心依賴的準確性。  
**SSOT (單一真實來源) 判定口徑**：

- 合夥人視角：Telegram `/daily` 輸出。
- 全域總表：`data/state/system_health_latest.json`
- 證據來源：`freshness_table.json` / `coverage_matrix_latest.json` / `strategy_pool*.json`

| 檢查項目 | PASS 條件 | FAIL 時 SOP (下一步) |
| :--- | :--- | :--- |
| **Freshness (新鮮度)** | /daily 顯示延遲 < 5min，證據與 system_health 吻合。 | 1. 執行 `bash scripts/refresh_state.sh` 強制刷新。<br>2. 再次檢查 /daily 若仍 FAIL，請排查 ETL。 |
| **Coverage (覆蓋率)** | /daily 顯示 100% 覆蓋，無資料遺失。 | 1. 執行 `bash scripts/refresh_state.sh`。<br>2. 若無法恢復，執行回補腳本 (backfill)。 |
| **Lineage (血緣)** | 所有產出物 (如 backtest summary) 皆能溯源至明確版本。 | 暫緩決策，人工清查產出腳本的 Git SHA 標籤。 |

## C. 研究可用性 (Research Availability)

驗證策略在不同環境下的表現及對照安全性，避免評估偏差。

| 檢查項目 | PASS 條件 | FAIL 時 SOP (下一步) |
| :--- | :--- | :--- |
| **樣本數遞增** | 回測總樣本數 (Trades) 確實隨時間增加，無停滯。 | 檢查過濾條件 (Gate) 是否過於嚴苛，或資料灌入失敗。 |
| **Regime Slicing (切片)** | `/daily` 必須明確顯示：<br>1. `regime_slice` (如 bull/bear/ALL)<br>2. `regime_window_utc` (格式 `[start,end)` )<br>3. `fallback_reason` (若為 ALL 的原因碼) | 確認 Regime Timeline SSOT 是否缺少當下定義，或切片系統脫鉤。 |
| **Leaderboard (榜單隔離)** | Leaderboard 與 Strategy Pool 必須利用 `slice_comparison_key` 區分不同 slice 的成績，絕不混在同一個 Entry 中。 | 拒絕該 PR，要求修復彙整邏輯，隔離不同 Regime 的分數計算。 |

## D. 治理可用性 (Governance Availability)

保證策略上架流程自動化、防呆且合夥人能輕量決策。

| 檢查項目 | PASS 條件 | FAIL 時 SOP (下一步) |
| :--- | :--- | :--- |
| **冷卻與去重 (Cooldown/Dedupe)** | 剛被淘汰的策略進入冷卻期，同樣參數的策略不會重複提交。 | 拒絕操作，檢查 dedupe 檢查的 hash function 邏輯。 |
| **草稿預檢 (PR Draft First)** | 上架提案必須先是 Draft PR，通過 CI (smoke/diff) 才能轉正。 | 將 PR 轉回 Draft，修復 CI 直至綠燈。 |
| **十分鐘決策 (10-min Review)** | 合夥人能在 10 分鐘內看完報告決定 `Merge` 或 `Close`。 | 報告過於冗長或資訊不足，需重新收斂 `/daily` 輸出。 |
| **一鍵撤回 (Rollback)** | 發生錯誤時可隨時退回上一版。 | 緊急執行 `git revert <merge_commit_sha>` 並重構。 |
