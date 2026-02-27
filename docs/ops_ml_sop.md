> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# ML Operations 每日維運手冊 (SOP)

這是一份針對 HONGSTR 機器學習分析輔助模組 (Phase 5&6) 的維運手冊。
請記住：**ML 顧問僅提供唯讀的歷史分析佐證 (Evidence)，完全不會觸碰到實盤交易或下單核心。**

## 1. 什麼時候需要執行？

當您想為剛收集完畢的當下市場資料 (Daily ETL)，打上最新的看漲/看跌評分，或者是想拿最新的數據回測既有策略時，便可手動依序執行本手冊。
（目前無需設定任何自動化 Scheduled Tasks）

## 2. 每日更新流程指令 (Daily Routine)

請依序複製並在您的終端機內貼上執行。整個過程只會寫入到 `reports/` 或 `data/` 資料夾，完全安全。

### Step 1: 確認基礎資料無縫接軌 (Coverage Check)

確保我們有最新的 K 線可以吃。

```bash
bash scripts/check_data_coverage.sh
```

*(如果出現 FAILED，請聯絡工程檢查 API 或重新跑 ETL)*

### Step 2: 建立技術指摽與市場特徵 (Build Features)

這會掃瞄最新的行情並建立特徵矩陣。

```bash
bash scripts/build_features.sh --freq 1h --symbols "BTCUSDT ETHUSDT BNBUSDT" --start 2020-01-01 --end now
```

### Step 3: 計算未來的標籤 (Build Labels)

讓機器知道到底後面 24 小時有沒有漲。

```bash
bash scripts/build_labels.sh --freq 1h --horizon 24
```

### Step 4 & 5: 訓練並產出模型 (Train & Artifact)

```bash
bash scripts/run_ml_baseline.sh --freq 1h --horizon 24
bash scripts/build_model_artifact.sh --freq 1h --horizon 24
```

### Step 6: 替這批數據打分數 (Build Signals)

最重要的唯讀產物 `signal_1h_24.parquet` 會在這裡產生。

```bash
bash scripts/build_signals.sh --freq 1h --horizon 24
```

### Step 7: 讓回測系統偷看一下這些分數 (Backtest Hook) [選擇性]

在回測你的策略時，帶上這個 Parquet 並指定 `report_only`，他就會把打分紀錄在回報結果中，但**不會**介入交易。

```bash
.venv/bin/python scripts/run_backtest.py \
  --signal-parquet reports/research/signals/signal_1h_24.parquet \
  --signal-policy report_only \
  --symbols BTCUSDT --timeframes 1h \
  --start 2025-01-01 --end 2025-02-01
```

### Step 8: 分析報告出爐 (Evidence Summary)

生成讓非工程夥伴一看就懂的 Markdown 中文總結報告。

```bash
.venv/bin/python scripts/report_ml_evidence.py --freq 1h --horizon 24 --latest-backtest auto
```

**您可以直接查閱 `reports/research/ml/evidence_summary.md` 來看結論！**

---

## 3. 常見問題排除 (Troubleshooting)

- **Q: Coverage 一直失敗怎麼辦？**
  A: 優先確認您的幣安連線是否正常，若差距太大可以手動執行 `python scripts/ingest_historical.py` 及 `scripts/aggregate_data.py` 將歷史大洞補齊。
- **Q: 畫面報錯找不到 xxx.parquet？**
  A: 請確認您是不是中間跳過了某一個 Step。特徵、標籤、模型、訊號 是一環結一環的。
- **Q: 執行這些指令會把硬碟灌爆嗎？為什麼 git status 沒看到它們？**
  A: 所有的 `.parquet` 與 `.pkl` 模型動輒數十 MB，我們已經將它們設定為安全忽略名單 (`.gitignore`)，因此您的版本庫會保持絕對的乾淨。
- **Q: 我需要開法拉利 (LLM / Ollama) 才能算這個嗎？**
  A: 不用！這全部都是傳統且極速的 Scikit-Learn 模型，一般的機器即可在幾十秒內解決幾何年的特徵運算。
