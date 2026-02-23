# Phase 0 Checkpoint: Strategy Pool & Semantics Governance

## 1. 現況總結 (Current State)

- **基礎覆蓋率 (Coverage)**：全部 PASS（包含 BTC, ETH, BNB 1m K線從 2020 至今的收取）。Daily ETL 與 Weekly Backfill 排程正常運作。
- **機器學習導入 (Phase 2-6)**：皆已完成，模型信號（`p_up`, `signal_score`）已經成功掛載到回測流程，且嚴格遵循 `report_only` 與 core diff=0 的無感染政策。
- **策略池管理 (Phase 0)**：在此次導入了策略與模型實驗庫的「管理機制」，讓散落各處的回測報表，收斂成一個清晰的「覆蓋率矩陣」與「候選策略晉升名單」。

## 2. 硬紅線防禦 (Hard Constraints Maintained)

- **Core Diff = 0**：`src/hongstr/` 核心撮合引擎 0 行被修改，維持絕對安全。
- **Parquet / PKL Not Tracked**：所有超過 MB 等級的特徵、標籤、與機器學習權重檔已完全隔離在 `reports/` 或 `data/` 下，且 git 無追蹤記錄。
- **Launchd Untouched**：所有的系統排程 (`ops/launchagents`) 完全沒有被本次更動波及。
- **Telegram CP Untouched**：本次作業未修改任何 Telegram Control Panel 代碼。

## 3. 新增的機制與管理檔案 (New Components)

1. **策略池名單 (`data/state/strategy_pool.json`)**
   這是一個追蹤哪支策略表現最好（候補 vs 正選）的記錄檔，可配合 `configs/strategy_pool_v1.json` 來決定晉升/下放的嚴謹度。
2. **回測覆蓋表 (`data/state/coverage_table.jsonl`)**
   紀錄了目前所有執行過的參數組合與標的的回測健康度是 `DONE`, `IN_PROGRESS`，還是 `BLOCKED`。每次回測完，透過 `python scripts/coverage_update.py` 自動寫入。
3. **語意版本卡控 (`configs/semantics_version.json`)**
   當我們修改了底層成本或是重要的金融邏輯時，升級此版的號碼，並執行 `python scripts/semantics_check.py`，就能自動將舊有的覆蓋表成績標註為需要重測 (`NEEDS_REBASE`)，確保實盤前的成績皆為最新口徑！
4. **Dashboard 儀表板整合**
   現在在您本機的網頁 Dashboard 上，已能夠「唯讀 (Read-only)」的監看上方兩個全新機制的現況數量與排行榜。

## 4. Phase 0.2 一鍵快照與儀表板優化 (Dashboard-Friendly Snapshots)

- **新增了一鍵彙整腳本 `scripts/refresh_state.sh`**：手動執行，不會自動上排程。負責依序呼叫各種狀態更新腳本，最終打印出一份易讀的 TL;DR 給營運人員驗收。
- **新增了 `scripts/state_snapshots.py` 摘要引擎**：針對巨大且肥厚的 `.jsonl` 歷史覆蓋檔進行精煉，產出了 `coverage_latest.json`, `coverage_summary.json`, 以及 `strategy_pool_summary.json` 三支經過計算的**小快取檔**。
- **前端 Dashboard API 升級體驗 (`route.ts`)**：當需要渲染策略池與 Coverage 矩陣時，伺服器現在會優先讀取剛剛說的「輕量化快取檔」，避免隨著回測次數增加，導致首頁開啟緩慢，且保有 fallback （若檔案不存在則讀取舊數據）的高可用性。
- **新增說明文件 `docs/ops_state_refresh.md`**：已產出「什麼是的一鍵重整」的白話合夥人說明手冊。

## 5. 下一步 (Next Steps / DoD)

- **HONG vs B&H 對決**：將晉升的優化策略正式派送，與單純買入持有 (Buy and Hold) 做最終的基準測試。
- **策略池自動剔除試車**：實際讓系統連續跑一週或特定時間，觀察 Strategy Pool 是否能如預期的產生 Anti-churn（不隨機頻繁上下架）的穩定性。
