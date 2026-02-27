> [!IMPORTANT] REFERENCE ONLY - Please see [Daily Report & Glossary](docs/ops/daily_report_zh.md) for current entry point.

# Research Poller SOP (v1.1)

每 10 分鐘由 launchd 自動觸發，檢查 `trigger_queue.jsonl` 是否有待處理事件。

- **冷卻 (Cooldown)**: 若距離上次 Loop 結束未滿 10 分鐘，狀態會寫入 `cooldown_skip`。
- **去重 (Dedupe)**: 一小時內重複的 trigger 不會重複 Enqueue。

## 常用指令

### 安裝與升級 (Install/Upgrade)

```bash
# 1. 複製排程設定
cp config/com.hongstr.research_poller.plist ~/Library/LaunchAgents/

# 2. 重新加載並啟動
launchctl unload ~/Library/LaunchAgents/com.hongstr.research_poller.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.hongstr.research_poller.plist

# 3. 檢查狀態 (期待 exit code 0)
launchctl list | grep research_poller
```

### 查看狀態與日誌

```bash
# 查看 Poller 最後運行狀態
cat data/state/_research/poller_last.json

# 追蹤排程日誌
tail -f logs/launchd_research_poller.out.log
```

### 手動 Enqueue 測試

```bash
# 測試去重：同一個 trigger 一小時內只會進隊列一次
PYTHONPATH=. .venv/bin/python -c "from research.loop.trigger_queue import enqueue; enqueue({'trigger': 'manual_test', 'source': 'ops'})"
```

## 回滾指令 (Rollback)

```bash
# 1. 停用排程
launchctl unload ~/Library/LaunchAgents/com.hongstr.research_poller.plist
rm -f ~/Library/LaunchAgents/com.hongstr.research_poller.plist

# 2. 還原程式碼
git checkout origin/main -- \
  scripts/poll_research_loop.sh \
  config/com.hongstr.research_poller.plist \
  research/loop/trigger_queue.py \
  _local/telegram_cp/tg_cp_server.py \
  scripts/daily_backtest.sh \
  docs/ops_research_poller.md

# 3. 清理狀態檔 (不影響歷史報告)
rm -rf data/state/_research/poller_last.json data/state/_research/trigger_queue.*
```

> [!NOTE]
> 本系統遵循**穩定性優先**原則。Poller 永遠以 code 0 結束，失敗僅反映在 `poller_last.json`。
