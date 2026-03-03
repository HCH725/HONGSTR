# HONGSTR ML Signal Architecture (Phase 5)

**給非工程合夥人的快速導覽 (TL;DR)**

- **這包程式碼在做什麼？** 負責將我們的機器學習 (ML) 歷史研究成果，打包成標準化的「訊號分數 (Signal Score)」，並且在不改變任何下單與撮合邏輯的前提下，把這些分數變成一份「報告擴充包」。
- **有沒有亂動核心交易？** 絕對沒有。所有的預測模型都只負責產出一個分數 (範圍從 -1 到 1)，這就像是給每根 K 線打個「看漲/看跌的參考星等」。
- **什麼是 `report_only`？** 我們在執行歷史回測時，可以加上一個「只提供報告 (`report_only`)」的開關。開了以後，系統一樣會按照既有策略下單，但會在最後的總結報告裡，告訴我們這個預測模型當時對這些交易的看法是什麼，作為策略評估的額外綠葉佐證。

---

### 詳細運作階段 (The Pipeline)

> **[聲明] IBM ML 文章僅為概念參考**  
> 本專案的設計曾參考 IBM 等外部文獻作為檢核清單與概念發想，但這**不代表**我們必須或將要導入其複雜的 production pipeline。任何新演算法的導入，都必須嚴守本專案的「四大天條」：1) Core diff = 0 2) 純 report_only 輔助 3) 隨時可拔（可回退）4) 不追蹤龐大 Parquet 檔案。

整個信號的產生與應用分為三個步驟，全部在 `research/` 與 `scripts/` 完成：

1. **資料特徵與標籤 (Features & Labels)**
   - **Features (特徵)**: 每一筆行情（例如 BTC 1小時 K線），我們將其轉化為幾十個市場特徵 (例如 RSI, 趨勢力度, 波動率)。
   - **Labels (標籤)**: 也就是未來的「答案」。例如「24小時後的漲幅是多少」、「是否超過均線上漲」。

2. **模型訓練與打包 (Model Artifacts)**
   - 我們訓練了 Logistic Regression (分類機率) 與 Ridge (幅度預測) 兩種輕量化的 Baseline 模型。
   - 輸出的模型會被嚴格序列化並封裝在 `reports/research/models/`，裡頭附帶嚴格的防偽特徵如時間戳與 Git Commit 版本號。

3. **訊號產生與回測勾稽 (Signal Parquet & Backtest Hook)**
   - **Signal Parquet**: 也就是所謂的「預測信號表」。模型讀取最新的 Features 後，會吐出一份包含每一時刻勝率與預期幅度的清單，最終融合成 `signal_score`。
   - **Backtest Hook**: 執行回測時 (例如 Phase 2 參數掃描時)，背後引擎只會*偷看*這份訊號表，並將它的統計分布 (Coverage, Mean Score) 加註到輸出的 `summary.json` 中，我們稱之為 **ML Evidence (機器學習證據)**。

### 開發者指令重現

對於需要重新生成 Artifacts 或是執行完整端到端測試的夥伴，只需要按順序執行以下 bash 腳本：

```bash
# 1. 重建特徵與標籤 (1小時頻率, 24小時預測期)
bash scripts/build_features.sh --freq 1h --symbols "BTCUSDT ETHUSDT BNBUSDT" --start 2020-01-01 --end now
bash scripts/build_labels.sh --freq 1h --horizon 24

# 2. 跑 Baseline 並打包模型 Artifact
bash scripts/run_ml_baseline.sh --freq 1h --horizon 24
bash scripts/build_model_artifact.sh --freq 1h --horizon 24

# 3. 讀取 Artifact 產生推論訊號 parquet (-1到1的分數)
bash scripts/build_signals.sh --freq 1h --horizon 24

# 4. 指定 --signal-policy report_only 將推論掛入回測報告
.venv/bin/python scripts/run_backtest.py --signal-parquet reports/research/signals/signal_1h_24.parquet --signal-policy report_only --symbols BTCUSDT --timeframes 1h --start 2025-01-01 --end 2025-02-01

# 5. 輸出白話文的 ML Evidence 摘要報告
.venv/bin/python scripts/report_ml_evidence.py --freq 1h --horizon 24 --latest-backtest auto
```

如果您執行了第五個步驟，您可以打開 `reports/research/ml/evidence_summary.md` 直接閱讀供非工程人員理解的分析總結。

執行後可以在 `data/backtests/.../summary.json` 裡面找到 `ml_evidence` 的 JSON block，宣告掛載成功！
