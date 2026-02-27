# HONGSTR 每日營運摘要與術語對照 (zh-TW)

> 本文件是 HONGSTR 系統營運的「單一入口」，旨在幫助合作夥伴理解系統狀態與專業術語。

---

## 1. 如何閱讀 `/daily` 報告 (Daily Report Guide)

每日系統會產出營運報告，請重點關注 **系統健康 (System Health)** 與 **市場風險 (Regime Signal)**。

- **SSOT Status (系統連貫性)**: ✅ OK 代表數據與狀態文件同步正常。
- **Regime Signal (市場風險訊號)**: 🟢 低風險可開倉；🔴 高風險暫避。
- **Backtest Head (最新回測)**: 最近 24 小時的模擬績效。
- **G0-G6 (治理門檻)**: 數字越大代表該策略通過的審核越嚴格。

---

## 2. 常用縮寫中英對照 (Acronym Glossary)

| 縮寫 | 全名 | 白話解釋 |
| :--- | :--- | :--- |
| **SSOT** | Single Source of Truth | 單一真理來源，確保系統看到的數據是一致的。 |
| **DD / MDD** | (Max) Drawdown | (最大) 回撤，指資產從最高點跌下來的幅度。 |
| **IS / OOS** | In-Sample / Out-of-Sample | 樣本內/樣本外。OOS 表現通常更接近實際市場。 |
| **WF** | Walk-Forward | 步進式測試，一種模擬策略隨時間演進的驗證方法。 |
| **L1/L2/L3** | Liquidity Levels | 流動性層級。L3 通常代表考慮深度影響後的成本。 |
| **DoD** | Definition of Done | 完成定義，研究任務必須滿足的最低門檻。 |
| **Gates** | Governance Gates | 治理三關六將。策略必須逐一過關才能增加部位。 |
| **Pool** | Strategy Pool | 策略池，目前正在運行的「貨架」策略。 |
| **Leaderboard** | Leaderboard | 英雄榜，顯示潛在的新策略候選人。 |

---

## 3. WARN / FAIL 白話 SOP

當報告出現黃燈 (WARN) 或 紅燈 (FAIL) 時：

- **SSOT Status: FAIL**
  - *解釋*: 數據同步中斷或文件毀損。
  - *SOP*: 執行 `bash scripts/refresh_state.sh`，若仍失敗請聯繫開發。
- **Regime Signal: FAIL**
  - *解釋*: **市場風險高，系統主動停止開倉**，並非程式出錯。
  - *SOP*: 保持觀望，不需進行技術修復。
- **Freshness: WARN**
  - *解釋*: 數據延遲超過 10 分鐘。
  - *SOP*: 檢查網路與 Binance API 連線狀況。
- **Overfit Gov: FAIL**
  - *解釋*: 發現策略有隱含的過度擬合（作弊）嫌疑。
  - *SOP*: 該策略必須打回研究階段，不可實際上線。

---

## 4. 進階參考連結 (Advanced Reference)

> [!NOTE]
> 以下文件僅供技術開發或深度審閱參考。

- **操作指南**: [Telegram Operator Manual](telegram_operator_manual.md)
- **數據檢核**: [Kline Freshness Checklist](../ops_kline_freshness_checklist.md)
- **治理細節**: [Overfit Gates Aggressive](../governance/overfit_gates_aggressive.md)
- **成本模型**: [DCA-1 Cost Model](../governance/dca1_cost_model.md)
- **系統清單**: [Repository Inventory](../inventory.md)

---
Safety Level: Docs Official (Partner-Facing)
