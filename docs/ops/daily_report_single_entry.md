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

## 3) Acronym 規則

`/daily` 首次出現縮寫必須附中文解釋：

- `SSOT`, `DD`, `MDD`, `Sharpe`, `Trades`, `OOS`, `IS`, `WF`, `L1`, `L2`, `L3`, `TP`, `SL`, `DCA`

來源：`docs/ops/acronym_glossary_zh.md`

## 4) 缺值規則（硬性）

- 指標缺值不得顯示 `0.00`
- 一律使用：`null + metrics_status=UNKNOWN + metrics_unavailable_reason`
- `/daily` 顯示為：`資料不足/UNKNOWN`

## 5) LLM 潤飾策略

- 預設先生成 deterministic fallback（固定模板）
- 若 reasoning client 可用，僅做文字潤飾
- 若 LLM 失敗或 timeout：`DAILY_REPORT_STATUS: WARN`，並回退 deterministic fallback

## 6) 需要深入時去哪看（Reference only）

- `docs/inventory.md`
- `docs/ops/telegram_operator_manual.md`
