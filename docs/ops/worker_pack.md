# HONGSTR Worker Pack (macOS-only) MVP

> **Primary Ops Entry (Worker)**
> 目的：提供可 24/7 跑雙任務（research + backtests）的 macOS Worker Pack，預設維持 `report_only`。

## Scope / Red Lines

- `src/hongstr/**` 不可修改（core diff=0）。
- tg_cp 維持 no-exec（不得 `subprocess` / `os.system` / `Popen`）。
- 研究與回測預設 `report_only`。
- `data/**` 僅為執行產物，不可提交 git。
- 治理模式維持 semi-auto（除 docs-only 且明確允許外，不自動合併）。

## Primary Checklist

- PR #126 acceptance checklist: <https://github.com/HCH725/HONGSTR/pull/126>
- Repo-local checklist: [Worker Acceptance Checklist](worker_acceptance_checklist.md)

## One-Click Install (Fresh MacBook Air M4)

```bash
# 1) clone once
git clone git@github.com:HCH725/HONGSTR.git ~/Projects/HONGSTR

# 2) bootstrap (idempotent)
cd ~/Projects/HONGSTR
bash scripts/worker_pack_bootstrap.sh

# 3) choose job (open two terminals for dual jobs)
bash scripts/worker_run_research.sh
bash scripts/worker_run_backtests.sh
```

## Runtime Jobs

- `scripts/worker_run_research.sh`
  - 每次執行前 `git fetch/pull main`（ff-only）
  - 呼叫 `bash scripts/run_research_loop.sh --once`（必要時可加 `HONGSTR_WORKER_RESEARCH_DRY_RUN=1`）
  - 輸出 heartbeat 與 last_run JSON 到 `_local/worker_state/`
- `scripts/worker_run_backtests.sh`
  - 每次執行前 `git fetch/pull main`（ff-only）
  - 呼叫 `bash scripts/run_and_verify.sh --mode foreground --no_fail_on_gate ...`
  - 輸出 heartbeat 與 last_run JSON 到 `_local/worker_state/`

## Cooldown Scheduling (80% utilization target)

兩個 job 都採同樣排程：`run N minutes` + `sleep M minutes`。

- `HONGSTR_WORKER_RUN_MINUTES=40` (default)
- `HONGSTR_WORKER_SLEEP_MINUTES=10` (default)
- `HONGSTR_WORKER_BETWEEN_RUNS_SECONDS=5` (default)
- `HONGSTR_WORKER_ONCE=1` 可只跑一輪（驗證/除錯用）

## Worker State Files (Pull Model)

Worker 本地輸出（不改 main SSOT writer semantics）：

- `_local/worker_state/worker_heartbeat.json`
- `_local/worker_state/last_run_research.json`
- `_local/worker_state/last_run_backtests.json`

主機採 pull model 擷取（Tailscale + SSH/rsync）：

```bash
# run on main host
rsync -avz <user>@<worker-tailnet-ip>:<REPO_DIR>/_local/worker_state/*.json \
  <REPO_DIR>/_local/worker_state_workers/worker-air-m4/
```

## Connectivity (Default)

- 建議：Tailscale tailnet + SSH key（禁用密碼）。
- Worker 可在不同網段；主機用 pull model 定時抓 `_local/worker_state/*.json`。
- 如需人工檢查，直接登入 worker 看 `_local/worker_state/` 即可。

## launchd Examples

見 [Worker Pack launchd examples](worker_pack_launchd.md)。

## Verification Commands

```bash
bash scripts/install_hongstr_skills.sh --force
./.venv/bin/python -m pytest -q _local/telegram_cp/test_local_smoke.py
./.venv/bin/python -m pytest -q research/loop/tests

git diff --name-only origin/main...HEAD | rg '^src/hongstr/' && exit 1 || true
rg -n 'subprocess|os\.system|Popen' _local/telegram_cp/tg_cp_server.py && exit 1 || true
git status --porcelain | rg '^.. data/' && exit 1 || true
```
