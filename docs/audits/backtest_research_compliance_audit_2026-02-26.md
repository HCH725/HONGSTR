# HONGSTR Backtest & Research Compliance Audit (Stability-first)

Date (UTC): 2026-02-26  
Scope: Backtest cadence/params/gates, research loop readiness, tg_cp quant skill schema/help alignment  
Mode: report_only (no trading behavior changes)

## Executive Summary

| Area | Status | Notes |
|---|---|---|
| Backtest pipeline cadence + artifacts | PASS | `daily_backtest` schedule and `summary/gate/selection` artifact chain are present and verifiable. |
| IS/OOS split + gate thresholds source-of-truth | PASS | Split constants and gate thresholds are centralized and traceable to code/config. |
| Research loop operating + outputs verifiable | WARN | Loop/poller run, proposals/results exist, Reasoning Model JSON contract works; research leaderboard refresh is stale. |
| Strategy pool / leaderboard defaults consistency | WARN | Strategy pool summary follows expected default ranking; research leaderboard update cadence appears broken/stale. |
| tg_cp quant skill help/schema UX | FAIL | `/skills help` behavior and `/run help`/error payloads are not yet aligned with requested richer contract. |

---

## A) Inventory (Source-of-Truth Mapping)

### 1) Backtest schedule + orchestration

- Launchd schedule source:
  - `ops/launchagents/com.hongstr.daily_backtest.plist`: daily `05:00`
  - Installed runtime: `~/Library/LaunchAgents/com.hongstr.daily_backtest.plist`
- Backtest runner chain:
  - `scripts/daily_backtest.sh` -> `scripts/run_and_verify.sh`
  - `run_and_verify.sh` generates in order:
    1. `summary.json` (from `scripts/run_backtest.py`)
    2. `optimizer.json`
    3. `regime_report.json`
    4. `gate.json` (`scripts/generate_gate_artifact.py`)
    5. `optimizer_regime.json` (`scripts/generate_optimizer_regime_artifact.py`)
    6. `selection.json` (`scripts/generate_selection_artifact.py`)
    7. verify + gate summary + action items

### 2) Strategy definitions + default parameter sets

- Core strategy implementation:
  - `src/hongstr/signal/strategies/vwap_supertrend.py`
- Backtest default strategy + params source:
  - `scripts/run_backtest.py`
  - default `--strategy vwap_supertrend`
  - default params path:
    - base: `atr_period=10`, `atr_mult=3.0`
    - if timeframe is `4h`: `atr_mult=2.0`
- Strategy pool default snapshot source:
  - `data/state/strategy_pool.json`
  - observed candidate: `trend_mvp_btc_1h` (score `0.5`, OOS sharpe `1.2`)

### 3) Gate/scoring thresholds + enforcement

- Backtest gate config SSOT:
  - `configs/gate_thresholds.json`
- Enforcer:
  - `scripts/generate_gate_artifact.py`
  - uses adaptive required trades:
    - `required_trades = max(min_trades_portfolio_min, window_days * min_trades_per_day)`
  - evaluates by regime (`BULL/BEAR/NEUTRAL`) using mode thresholds (`FULL`/`SHORT`)
- Gate consumer:
  - `scripts/gate_summary.py` (prefers `gate.json`, legacy fallback if missing)
- Research gate SSOT:
  - `research/loop/gates.py` (`min_oos_sharpe=0.5`, `max_oos_mdd=-0.15`, `overfit_ratio=2.0`)

### 4) Selection + summary expected fields

- `summary.json` observed top-level fields:
  - `sharpe`, `max_drawdown`, `trades_count`, `per_symbol`, `config`, `start_ts`, `end_ts`, etc.
- `gate.json` observed fields:
  - `config`, `inputs`, `results.by_regime`, `results.overall.pass/reasons`
- `selection.json` observed fields:
  - `decision`, `selected`, `gate`, `candidates`, `reasons`
  - selected payload keys: `symbol`, `params`, `rank`, `score`

---

## B) SSOT Verification (Executed)

### 1) State refresh execution

- Executed: `bash scripts/refresh_state.sh`
- Result: success (`exit 0`)
- Generated/updated:
  - `data/state/system_health_latest.json`
  - `data/state/freshness_table.json`
  - `data/state/coverage_matrix_latest.json`
  - `data/state/regime_monitor_latest.json`
  - `data/state/brake_health_latest.json`

Observed from `data/state/system_health_latest.json`:

- `ssot_status=OK`
- `refresh_hint=bash scripts/refresh_state.sh`
- freshness thresholds include profile split:
  - `realtime`: `ok_h=0.1`, `warn_h=0.25`, `fail_h=1.0`
  - `backtest`: `ok_h=26.0`, `warn_h=50.0`, `fail_h=72.0`

### 2) Latest backtest artifact verification

- Latest run dir:
  - `data/backtests/2026-02-25/20260226_050003_f431`
- Parsed metrics:
  - `summary.json`: `sharpe=0.570803`, `max_drawdown=-0.139940`, `trades_count=3597`
  - `gate.json`: `overall.pass=true`, `reasons=[]`
  - `selection.json`: `decision=TRADE`, `selected.symbol=BTCUSDT`

### 3) Strategy pool + research leaderboard cadence

- Strategy pool:
  - `data/state/strategy_pool_summary.json` updated by `refresh_state.sh` (fresh)
  - leaderboard top entry: `trend_mvp_btc_1h`
- Research leaderboard:
  - file exists: `data/state/_research/leaderboard.json`
  - observed stale timestamp (older than latest `reports/research/*` results)
  - code audit finding: `research/loop/research_loop.py` imports `save_leaderboard` but does not call it

---

## C) Quant Specialist Readiness

### 1) Ollama/Reasoning Model readiness

- Model manifests present (as of audit date 2026-02-26; **deepseek-r1 decommissioned 2026-03-05**):
  - ~~`~/.ollama/models/manifests/registry.ollama.ai/library/deepseek-r1/7b`~~ (removed; migrated to qwen2.5)
  - `~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/7b-instruct`
  - `~/.ollama/models/manifests/registry.ollama.ai/library/qwen2.5/0.5b`
- Live reasoning client test (Reasoning Model via Ollama `/api/chat`):
  - returned normalized JSON contract
  - `actions=[]` enforced
  - keys present: `status/problem/key_findings/hypotheses/recommended_next_steps/risks/actions/citations/refresh_hint`

### 2) tg_cp `/skills` + `/run help` schema alignment checks (quant skills)

Audited skills:

- `backtest_reproducibility_audit`
- `factor_health_and_drift_report`
- `strategy_regime_sensitivity_report`

Observed current behavior:

- `/run <skill> key=value ...`: works
- `/run <skill> {"k":"v"}`: works
- `/run help <skill>`:
  - shows schema JSON
  - **example is generic and wrong** (`include_sources=true`) for quant skills
  - does **not** output `allowed_keys`
- unknown keys:
  - currently returns `參數錯誤: unknown keys: [...]` + `請用 /run help ...`
  - **does not include** `allowed_keys` or `refresh_hint`
- `/skills help <skill>`:
  - currently not supported as a dedicated help handler in this branch

Conclusion:

- Parsing capability: PASS (supports key=value + JSON object)
- Help/error contract richness: FAIL (missing requested diagnostics)

---

## D) SOP Compliance Notes

### What is source-of-truth for backtest params and gates

- Backtest gate thresholds: `configs/gate_thresholds.json`
- Backtest gate enforcement: `scripts/generate_gate_artifact.py`
- Research gate enforcement: `research/loop/gates.py`
- Split constants: `scripts/splits.py` (`IS_END_DATE=2024-12-31`, `OOS_START_DATE=2025-01-01`)

### Current cadence and freshness profile meaning

- `com.hongstr.daily_backtest`: daily `05:00`
- `com.hongstr.refresh_state`: `RunAtLoad + StartInterval=3600`
- `com.hongstr.daily_healthcheck`: daily `02:30` (alias path to `refresh_state.sh`)
- `com.hongstr.research_poller`: every `600s`
- `com.hongstr.research_loop`: daily `06:20`

Freshness profiles:

- `realtime` profile is strict (minute-scale)
- `backtest` profile is tolerant for daily batch cadence (26h/50h/72h bands)

### When results look wrong, check in this order

1. `bash scripts/refresh_state.sh`
2. `data/state/system_health_latest.json` (`ssot_status`, component statuses)
3. Latest `summary.json` metrics (`sharpe/max_drawdown/trades_count`)
4. `gate.json` overall pass/fail and reasons
5. `selection.json` decision/selected symbol
6. `reports/state_atomic/regime_monitor_latest.json` and `data/state/regime_monitor_latest.json`
7. Research outputs under `reports/research/<YYYYMMDD>/` and `data/state/_research/*`

---

## PM Audit Pack (Copy/Paste)

```bash
set -euo pipefail
REPO="/Users/hong/Projects/HONGSTR"
cd "$REPO"

echo "== Inventory =="
plutil -p ops/launchagents/com.hongstr.daily_backtest.plist
plutil -p ops/launchagents/com.hongstr.refresh_state.plist
plutil -p ops/launchagents/com.hongstr.research_poller.plist
plutil -p ops/launchagents/com.hongstr.research_loop.plist

echo "== SSOT Refresh =="
bash scripts/refresh_state.sh

echo "== SSOT Health =="
python3 - <<'PY'
import json
from pathlib import Path
p = Path("data/state/system_health_latest.json")
d = json.loads(p.read_text())
print("ssot_status:", d.get("ssot_status"))
print("refresh_hint:", d.get("refresh_hint"))
print("components:", d.get("components"))
PY

echo "== Latest Backtest Artifacts =="
python3 - <<'PY'
import glob, os, json
from pathlib import Path
run = max(glob.glob("data/backtests/*/*"), key=os.path.getmtime)
print("run_dir:", run)
for f in ["summary.json","gate.json","selection.json"]:
    p = Path(run)/f
    print(f, "exists=", p.exists())
    d = json.loads(p.read_text())
    if f=="summary.json":
        print(" sharpe=", d.get("sharpe"), "maxdd=", d.get("max_drawdown"), "trades=", d.get("trades_count"))
    if f=="gate.json":
        print(" gate_overall=", d.get("results",{}).get("overall",{}))
    if f=="selection.json":
        print(" decision=", d.get("decision"), "selected=", d.get("selected"))
PY

echo "== Quant Skill Contract Check =="
python3 - <<'PY'
import importlib
s = importlib.import_module("_local.telegram_cp.tg_cp_server")
skills = [
  "backtest_reproducibility_audit",
  "factor_health_and_drift_report",
  "strategy_regime_sensitivity_report",
]
for sk in skills:
    out, ok = s._handle_run(f"/run help {sk}")
    print("\\n[help]", sk, "ok=", ok)
    print(out)
    out2, ok2 = s._handle_run(f"/run {sk} foo=bar")
    print("[unknown]", sk, "ok=", ok2, "msg=", out2)
PY
```
