# PM 3-Minute Audit Checklist

旨在幫助 PM 快速確認系統狀態與策略健康度。

## 每日 /daily 檢核項目

- [ ] **SSOT Status**: 是否為 ✅ OK？
  - *若為 FAIL: 代表數據不連貫，不可信任今日報告。*
- [ ] **Regime Slice**: 標籤是否與預期相符（BULL/BEAR/SIDEWAYS）？
  - *解讀 BULL*: 重視趨勢獲利能力與滑價控制。
  - *解讀 BEAR*: 重視防守與策略在極端波動下的穩定性。
  - *解讀 SIDEWAYS*: 重視網格或均值回歸策略的效率。
- [ ] **Fallback Reason**: 是否出現降級？
  - *顯示 ALL (Empty)*: 代表目前測試的是「全時段」，不代表錯誤。
  - *常見原因*: 測試時間區間未在 `regime_timeline.json` 中完整覆蓋。
- [ ] **Regime Signal**: 是否為開倉准許（🟢 GREEN）？
  - *若為🔴 RED (FAIL)*: 代表環境風險高，系統主動暫避，不需修復。

---

## 例行維護

- [ ] **SSOT 同時性**: 確保 `data/state/` 下的文件不超過 15 分鐘未更新。
- [ ] **治理門檻**: 確保新加入 Pool 的策略至少通過 G4 審核。

---
Safety Level: Governance (zh-TW)
