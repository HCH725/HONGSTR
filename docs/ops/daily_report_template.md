# HONGSTR 每日營運報告模板 (v1)

> 本報告旨在為合作夥伴提供系統狀態與策略表現的快速概覽。

---

## 1. 系統健康 (System Health)

- **整體狀態**: SSOT Status（全域狀態）: ✅ OK / ⚠️ WARN / ❌ FAIL
- **數據新鮮度**: Freshness（數據延遲）: ✅ 正常（延遲 < 5min）
- **數據覆蓋**: Coverage（數據完整性）: ✅ 100%
- **安全剎車**: Brake（安全剎車）: ✅ 已部署
- **市場風險**: Regime Signal（市場風險訊號）: 🟢 低風險 / 🔴 高風險 (FAIL)
  - *註：FAIL 代表市場風險偏高進入「觀望」模式，不代表系統壞掉。*

## 2. 今日回測 (Today's Backtest)

- **回測 ID**: 2026-02-27-090000
- **最新表現 (Backtest Head)**:
  - 總回報: +2.4%
  - 最大回撤 (MDD): -1.5%
  - 夏普比率 (Sharpe): 1.8

## 3. 策略池與排行榜 (Strategy Pool & Leaderboard)

- **策略池狀態 (Strategy Pool)**: 目前有 3 支策略在「貨架」上。
- **排行榜前三 (Leaderboard)**:
  1. `trend_mvp_v1`: 分數 88 (高動能)
  2. `vbp_grid_v2`: 分數 75 (低波動捕捉)
  3. `ema_cross_v3`: 分數 72

## 4. 治理與模型健壯性 (Governance & Overfit)

- **治理門檻 (Gates)**: 今日所有上架策略皆通過 G4 (模擬成本) 以上審核。
- **過度擬合預警 (Overfit Governance)**: ✅ 正常。OOS (樣本外) 表現與模擬一致。

## 5. 紅線保護 (Red Line Protection)

- **核心變動**: 0 (核心程式碼未變動)
- **數據安全**: 無敏感數據提交
- **執行政策**: No-Exec 嚴格執行（報告模式）

---
*Safety Statement: 本報告由系統自動生成，僅供審閱，不涉及實際交易執行。*
