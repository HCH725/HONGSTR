# HONGSTR 每日營運報告與術語表 (zh-TW)
>
> [!IMPORTANT]
> **REFERENCE ONLY**
> 每日報告主入口已收斂至 [Daily Report Single Entry](daily_report_single_entry.md)。

---

## 1. 每日營運報告模板 (Daily Report Template)
>
> [!IMPORTANT]
> **REFERENCE ONLY**
> 每日報告協議說明請參見 [Daily Report Single Entry](daily_report_single_entry.md)。
> 旨在提供系統狀態與策略表現的快速概覽。

### 報告區段

1. **系統健康 (System Health)**
   - **整體狀態**: SSOT Status (全域狀態): ✅ OK / ⚠️ WARN / ❌ FAIL
   - **數據新鮮度**: Freshness (數據延遲): ✅ 正常 (延遲 < 5min)
   - **數據覆蓋**: Coverage (數據完整性): ✅ 100%
   - **安全剎車**: Brake (安全剎車): ✅ 已部署
   - **市場風險**: Regime Signal (市場風險訊號): 🟢 低風險 / 🔴 高風險 (FAIL)
     - *註：FAIL 代表市場風險偏高進入「觀望」模式，不代表系統壞掉。*

2. **今日回測 (Today's Backtest)**
   - **回測 ID**: YYYY-MM-DD-HHMMSS
   - **最新表現 (Backtest Head)**: 總回報 / MDD / Sharpe

3. **策略池與排行榜 (Strategy Pool & Leaderboard)**
   - **策略池狀態**: 目前在架策略數與異動。
   - **排行榜前三**: 表現最優的候選策略。

4. **治理與過度擬合 (Governance & Overfit)**
   - **治理門檻**: 策略通過的 Gate 級別 (如 G4)。
   - **過度擬合預警**: OOS 表現是否與模擬一致。

5. **紅線保護 (Red Line Protection)**
   - 核心程式碼變動數 / 數據安全檢查。

---

## 2. 術語名詞表 (Acronym Glossary)

| 縮寫 (Acronym) | 中文定義 | 為什麼重要 (Why it matters) | 出現 WARN/FAIL 怎麼辦 |
| :--- | :--- | :--- | :--- |
| **SSOT** | 單一真理來源 | 確保系統組件數據一致。 | 檢查 `refresh_state.sh` 運行情況。 |
| **System Health** | 系統健康度 | 基礎設施整體狀態。 | 若為 FAIL，暫停自動化決策。 |
| **Freshness** | 數據新鮮度 | 實時數據延遲。 | 檢查 ETL 任務與網路狀態。 |
| **Coverage** | 數據覆蓋率 | 歷史數據完整性。 | 補齊數據缺口，以免回測失效。 |
| **Brake** | 安全剎車 | 自動化防護機制。 | 若為 FAIL，人介入檢查執行環境。 |
| **Regime Monitor** | 市場環境監測 | 辨識市場趨勢與壓力。 | 調整策略參數，但不影響存活。 |
| **Regime Signal** | 市場風險訊號 | 信號開倉准許。 | **FAIL 代表風險高，不進場**；並非系統錯誤。 |
| **Backtest Head** | 回測前端結果 | 最近一次模擬核心數據。 | 觀測策略是否產生衰減。 |
| **Gates** | 治理門檻 | 上架門檻 (G0-G6)。 | 級別不足時不可加大部位。 |
| **Strategy Pool** | 策略池 | 已上架策略。 | 關注是否有策略被強制下架。 |
| **Leaderboard** | 排行榜 | 候選策略排名。 | 選取下一階段推廣對象。 |
| **Overfit Gov.** | 過度擬合治理 | 防止策略只對歷史有效。 | 若警告亮起，策略需打回研究。 |

---
Safety Level: Docs Official (zh-TW)
