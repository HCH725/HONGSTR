"""Smoke tests for the LLM-first tg_cp_server.

These tests validate:
  • guardrail still blocks dangerous requests
  • policy + skills contract unchanged
  • /commands work without LLM
  • conversation history accumulates
  • system prompt includes snapshot + memories
  • secrets are redacted
"""
import json
import importlib.util
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from _local.telegram_cp.schemas_reasoning import ReasoningAnalysis
from _local.telegram_cp.prompt_pack import build_system_prompt as build_prompt_pack_system_prompt, select_overlay

TEST_DIR = Path(__file__).resolve().parent
FIXTURES_DIR = TEST_DIR / "tests" / "fixtures"
INCIDENT_FIXTURES = FIXTURES_DIR / "incident_timeline"


def _sandbox_state(monkeypatch, tmp_path, s):
    monkeypatch.setattr(s, "STATE_DIR", tmp_path / "state")
    monkeypatch.setattr(s, "OFFSET_PATH", tmp_path / "state" / "offset.json")
    monkeypatch.setattr(s, "SESSION_PATH", tmp_path / "state" / "session_state.json")
    monkeypatch.setattr(s, "OPS_MEM", tmp_path / "state" / "ops_memory.jsonl")
    monkeypatch.setattr(s, "USER_MEM", tmp_path / "state" / "user_memory.jsonl")
    monkeypatch.setattr(s, "RUNTIME_LOG", tmp_path / "state" / "runtime.log")
    monkeypatch.setattr(s, "ALERTS_PENDING", tmp_path / "state" / "alerts_pending.jsonl")
    monkeypatch.setattr(s, "FOLLOWUP_QUEUE", tmp_path / "state" / "followup_queue.jsonl")
    s._ensure_state()


def _load_server():
    p = TEST_DIR / "tg_cp_server.py"
    spec = importlib.util.spec_from_file_location("tg_cp_server_testmod", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


# ── guardrail ──

def test_guardrail_blocks_action_request(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(1, "幫我重啟 dashboard", use_llm=False)
    assert route == "REFUSE"
    assert "read-only" in resp or "不能" in resp
    # should include safe SOP
    assert "healthcheck" in resp or "SOP" in resp or "手動" in resp


def test_guardrail_blocks_trade_request(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(2, "幫我買進 BTC", use_llm=False)
    assert route == "REFUSE"
    assert "不能" in resp or "read-only" in resp


# ── policy + skills contract ──

def test_policy_and_skills_contract():
    policy = json.loads((TEST_DIR / "policy.json").read_text(encoding="utf-8"))
    skills = json.loads((TEST_DIR / "skills_registry.json").read_text(encoding="utf-8"))["skills"]

    assert policy["mode"] == "read_only"
    assert policy["allowed_actions"] == []
    names = [s["name"] for s in skills]
    assert set(names) >= {"status_overview", "logs_tail_hint"}


# ── commands work without LLM ──

def test_start_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(10, "/start")
    assert "中樞管家" in resp
    assert "不支援" not in resp
    assert "/status" in resp and "/help" in resp

    resp2 = s._handle_command(10, "/start@HONGSTR_bot")
    assert "中樞管家" in resp2


def test_help_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(20, "/help")
    assert "/status" in resp
    assert "/daily" in resp
    assert "/skills" in resp
    # Must list all monitoring commands so users can discover them
    assert "/freshness" in resp
    assert "/regime" in resp
    assert "/ml_status" in resp


# ── command routing: /freshness, /regime, /ml_status must NOT return 不認識 ──

def test_freshness_routing(monkeypatch, tmp_path):
    """Regression: /freshness must never return the 不認識 fallback."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    fake_snap = {"freshness": {
        "BTCUSDT": {"1m": {"age_hours": 1.0, "status": "OK"}, "1h": {"age_hours": 1.0, "status": "OK"}, "4h": {"age_hours": 1.0, "status": "OK"}},
        "ETHUSDT": {"1m": {"age_hours": 1.0, "status": "OK"}, "1h": {"age_hours": 1.0, "status": "OK"}, "4h": {"age_hours": 1.0, "status": "OK"}},
        "BNBUSDT": {"1m": {"age_hours": 1.0, "status": "OK"}, "1h": {"age_hours": 1.0, "status": "OK"}, "4h": {"age_hours": 1.0, "status": "OK"}},
    }}
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    resp = s._handle_command(20, "/freshness")
    assert "不認識" not in resp
    assert "新鮮度" in resp


def test_regime_routing(monkeypatch, tmp_path):
    """Regression: /regime and /regime_status must never return the 不認識 fallback."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    # No summary file → should return UNKNOWN guidance, not 不認識
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    for cmd in ["/regime", "/regime_status"]:
        resp = s._handle_command(20, cmd)
        assert "不認識" not in resp, f"{cmd} returned 不認識 — routing is broken"
        assert "Regime" in resp or "機制" in resp or "UNKNOWN" in resp


def test_ml_status_routing(monkeypatch, tmp_path):
    """Regression: /ml_status must never return the 不認識 fallback."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    resp = s._handle_command(20, "/ml_status")
    assert "不認識" not in resp, "/ml_status returned 不認識 — routing is broken"
    assert "ML" in resp or "Pipeline" in resp



def _write_status_ssot_sources(repo: Path) -> None:
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "freshness_table.json").write_text(
        json.dumps(
            {
                "rows": [
                    {"symbol": "BTCUSDT", "tf": "1m", "age_h": 1.2, "status": "OK"},
                    {"symbol": "ETHUSDT", "tf": "1h", "age_h": 2.3, "status": "WARN"},
                ]
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "coverage_matrix_latest.json").write_text(
        json.dumps(
            {
                "rows": [{"symbol": "BTCUSDT", "tf": "1h", "lag_hours": 0.0, "status": "PASS"}],
                "totals": {"done": 1, "inProgress": 0, "blocked": 0, "rebase": 0},
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "brake_health_latest.json").write_text(
        json.dumps(
            {
                "overall_fail": False,
                "results": [{"item": "Freshness Table", "status": "OK"}],
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "regime_monitor_latest.json").write_text(
        json.dumps({"overall": "OK"}),
        encoding="utf-8",
    )
    (state_dir / "coverage_table.jsonl").write_text(
        json.dumps(
            {
                "coverage_key": {"symbol": "BTCUSDT", "timeframe": "1h"},
                "status": "DONE",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _write_daily_report_ssot(repo: Path) -> None:
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "daily_report_latest.json").write_text(
        json.dumps(
            {
                "schema": {"version": "daily_report.v1", "field_labels_zh_en": {}},
                "generated_utc": "2026-02-27T00:00:00Z",
                "refresh_hint": "bash scripts/refresh_state.sh",
                "ssot_status": "OK",
                "ssot_components": {
                    "freshness": {"status": "OK"},
                    "coverage_matrix": {"status": "PASS"},
                    "brake": {"status": "OK"},
                    "regime_monitor": {"status": "OK"},
                    "regime_signal": {
                        "status": "FAIL",
                        "top_reason": "MDD 跌破保護線",
                        "threshold_value": -0.0353,
                        "threshold_source_path": "reports/strategy_research/phase3/phase3_results.json",
                        "threshold_policy_sha": "abc123def4567890",
                        "threshold_rationale": "最大回撤超過 p95 風險區間",
                        "calibration_status": "STALE",
                        "last_calibrated_utc": "2026-02-18T00:00:00Z",
                    },
                },
                "freshness_summary": {
                    "counts": {"OK": 8, "WARN": 1, "FAIL": 0, "UNKNOWN": 0},
                    "profile_totals": {"realtime": 6, "backtest": 3},
                    "total_rows": 9,
                    "max_age_h": 2.4,
                    "top_offenders": [
                        {"symbol": "ETHUSDT", "tf": "4h", "profile": "backtest", "age_h": 2.4, "status": "WARN"}
                    ],
                },
                "latest_backtest_head": {
                    "source": "local",
                    "path": "reports/research/20260227/trend_mvp_btc_1h__long__baseline/summary.json",
                    "bundle": None,
                    "timestamp": "2026-02-27T22:20:01Z",
                    "timestamp_utc": "2026-02-27T22:20:01Z",
                    "reason": "local backtest newer or equal to worker bundle",
                    "candidate_id": "trend_mvp_btc_1h__long__baseline",
                    "direction": "LONG",
                    "metrics_status": "OK",
                    "metrics": {
                        "final_score": 88.5,
                        "oos_sharpe": 1.2,
                        "oos_mdd": -0.09,
                        "is_sharpe": 1.4,
                        "trades_count": 37,
                    },
                    "gate": {"overall": "PASS"},
                },
                "strategy_pool": {
                    "summary": {"counts": {"candidates": 3, "promoted": 1, "demoted": 2}},
                    "leaderboard_top": [
                        {
                            "strategy_id": "trend_mvp_btc_1h",
                            "direction": "LONG",
                            "score": 88.5,
                            "oos_sharpe": 1.2,
                            "oos_return": 2.1,
                            "metrics_status": "OK",
                        },
                        {
                            "strategy_id": "ema_cross_v3",
                            "direction": "SHORT",
                            "score": None,
                            "oos_sharpe": None,
                            "oos_return": None,
                            "metrics_status": "UNKNOWN",
                        },
                    ],
                    "direction_coverage": {
                        "counts": {"long": 2, "short": 1, "longshort": 0, "unknown": 0},
                        "short_coverage": {
                            "candidates": 1,
                            "gate_pass": 1,
                            "best_entry": {
                                "strategy_id": "ema_cross_v3",
                                "score": None,
                                "metrics_status": "UNKNOWN",
                            },
                            "best_entry_reason": None,
                        },
                    },
                },
                "governance": {
                    "overfit_gates_policy": {"name": "aggressive_yield_first_v1"},
                    "today_gate_summary": {"scope": "today_utc", "pass": 1, "warn": 0, "fail": 1, "unknown": 1},
                },
                "guardrails": {
                    "status": "PASS",
                    "checks": {
                        "core_diff_src_hongstr": {"status": "PASS_EXPECTED"},
                        "tg_cp_no_exec": {"status": "PASS_EXPECTED"},
                        "no_data_committed": {"status": "PASS_EXPECTED"},
                    }
                },
                "sources": {
                    "worker_inbox": {
                        "present": True,
                        "latest_bundle": "mba_m4_backtests_20260227T210000Z",
                        "bundle_path": "_local/worker_inbox/mba_m4_backtests_20260227T210000Z",
                        "bundle_ts_utc": "2026-02-27T21:00:00Z",
                        "ingested_into_state": True,
                        "note": "worker 較舊，沿用 local",
                    }
                },
            }
        ),
        encoding="utf-8",
    )


def test_status_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    resp = s._handle_command(30, "/status")
    assert "SSOT_STATUS:" in resp
    assert "Sources:" in resp
    assert "freshness_table.json" in resp
    assert "coverage_matrix_latest.json" in resp
    assert "Dashboard lag 37.5h" not in resp
    assert "SSOT_SEMANTICS: SystemHealth only" in resp
    assert "Freshness:" in resp
    assert "CoverageMatrix: PASS" in resp
    assert "RegimeMonitor:" in resp
    assert "RegimeSignal:" in resp


def test_status_command_with_bot_suffix(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    resp_plain = s._handle_command(31, "/status")
    resp_suffix = s._handle_command(31, "/status@HONGSTR_bot")
    resp_ws = s._handle_command(31, "   /status   ")
    assert resp_plain == resp_suffix == resp_ws
    assert "Sources:" in resp_suffix
    assert "freshness_table.json" in resp_suffix
    assert "coverage_matrix_latest.json" in resp_suffix
    assert "CoverageMatrix: PASS" in resp_suffix


def test_status_command_unknown_when_ssot_missing(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)

    resp = s._handle_command(32, "/status@HONGSTR_bot")
    assert "SSOT_STATUS: UNKNOWN" in resp
    assert "missing=[" in resp
    assert "freshness_table.json" in resp
    assert "coverage_matrix_latest.json" in resp
    assert "RegimeMonitor: UNKNOWN" in resp
    assert "RegimeSignal: UNKNOWN" in resp
    assert "RefreshHint: Run: `bash scripts/refresh_state.sh`" in resp
    assert "Sources:" in resp


def test_status_command_unknown_when_partial_ssot_missing(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    (state_dir / "brake_health_latest.json").unlink()

    resp = s._handle_command(32, "/status")
    assert "SSOT_STATUS: UNKNOWN" in resp
    assert "missing=[brake_health_latest.json]" in resp
    assert "RefreshHint: Run: `bash scripts/refresh_state.sh`" in resp
    assert "Dashboard lag" not in resp


def test_status_command_unknown_when_ssot_unreadable(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    (state_dir / "coverage_matrix_latest.json").write_text("{", encoding="utf-8")

    resp = s._handle_command(32, "/status")
    assert "SSOT_STATUS: UNKNOWN" in resp
    assert "unreadable=[coverage_matrix_latest.json]" in resp
    assert "RefreshHint: Run: `bash scripts/refresh_state.sh`" in resp


def test_status_regime_signal_fail_does_not_flip_ssot(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    (state_dir / "freshness_table.json").write_text(
        json.dumps({"rows": [{"symbol": "BTCUSDT", "tf": "1m", "age_h": 1.0, "status": "OK"}]}),
        encoding="utf-8",
    )
    (state_dir / "regime_monitor_latest.json").write_text(
        json.dumps({"overall": "FAIL", "reason": ["MDD breach"]}),
        encoding="utf-8",
    )

    resp = s._handle_command(33, "/status")
    assert "SSOT_STATUS: OK" in resp
    assert "RegimeMonitor: OK" in resp
    assert "RegimeSignal: FAIL (MDD breach)" in resp


def test_status_regime_monitor_stale_affects_health(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    (state_dir / "freshness_table.json").write_text(
        json.dumps({"rows": [{"symbol": "BTCUSDT", "tf": "1m", "age_h": 1.0, "status": "OK"}]}),
        encoding="utf-8",
    )
    (state_dir / "regime_monitor_latest.json").write_text(
        json.dumps({"overall": "OK"}),
        encoding="utf-8",
    )
    old_ts = time.time() - (13 * 3600)
    os.utime(state_dir / "regime_monitor_latest.json", (old_ts, old_ts))

    resp = s._handle_command(34, "/status")
    assert "SSOT_STATUS: WARN" in resp
    assert "RegimeMonitor: WARN" in resp
    assert "RegimeSignal: OK" in resp


def test_status_prefers_system_health_pack_when_present(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    (state_dir / "system_health_latest.json").write_text(
        json.dumps(
            {
                "ssot_status": "WARN",
                "ssot_semantics": "SystemHealth only (RegimeSignal is separate trade-risk alert)",
                "refresh_hint": "bash scripts/refresh_state.sh",
                "components": {
                    "freshness": {"status": "OK", "max_age_h": 1.0},
                    "coverage_matrix": {"status": "WARN", "done": 0, "total": 1, "max_lag_h": 2.5, "rebase": 1},
                    "brake": {"status": "OK"},
                    "regime_monitor": {"status": "OK", "age_h": 0.2, "ok_within_h": 12},
                    "regime_signal": {"status": "FAIL", "top_reason": "MDD breach"},
                },
            }
        ),
        encoding="utf-8",
    )

    resp = s._handle_command(35, "/status")
    assert "SSOT_STATUS: WARN" in resp
    assert "CoverageMatrix: WARN 0/1 done | max_lag_h=2.5 | rebase=1" in resp
    assert "RegimeSignal: FAIL (MDD breach)" in resp
    assert "Sources: system_health_latest.json (preferred)" in resp


def test_status_health_pack_overrides_conflicting_component_files(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_status_ssot_sources(repo)
    monkeypatch.setattr(s, "REPO", repo)

    state_dir = repo / "data/state"
    # Conflicting component files should be ignored when health pack is present.
    (state_dir / "coverage_matrix_latest.json").write_text(
        json.dumps(
            {
                "rows": [{"symbol": "BTCUSDT", "tf": "1h", "lag_hours": 99.0, "status": "FAIL"}],
                "totals": {"done": 0, "inProgress": 0, "blocked": 1, "rebase": 0},
            }
        ),
        encoding="utf-8",
    )
    (state_dir / "regime_monitor_latest.json").write_text(
        json.dumps({"overall": "FAIL", "reason": ["component says fail"]}),
        encoding="utf-8",
    )
    (state_dir / "system_health_latest.json").write_text(
        json.dumps(
            {
                "ssot_status": "OK",
                "ssot_semantics": "SystemHealth only (RegimeSignal is separate trade-risk alert)",
                "refresh_hint": "bash scripts/refresh_state.sh",
                "components": {
                    "freshness": {"status": "OK", "max_age_h": 0.8},
                    "coverage_matrix": {"status": "PASS", "done": 1, "total": 1, "max_lag_h": 0.0, "rebase": 0},
                    "brake": {"status": "OK"},
                    "regime_monitor": {"status": "OK", "age_h": 0.1, "ok_within_h": 12},
                    "regime_signal": {"status": "OK", "top_reason": None},
                },
            }
        ),
        encoding="utf-8",
    )

    resp = s._handle_command(36, "/status")
    assert "SSOT_STATUS: OK" in resp
    assert "CoverageMatrix: PASS 1/1 done | max_lag_h=0.0 | rebase=0" in resp
    assert "RegimeSignal: OK" in resp
    assert "component says fail" not in resp


def test_daily_command_fallback_with_fixture(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_daily_report_ssot(repo)
    monkeypatch.setattr(s, "REPO", repo)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("timeout")))

    resp = s._handle_command(38, "/daily")
    assert "DAILY_REPORT_STATUS: WARN" in resp
    assert "1) SystemHealth" in resp
    assert "2) DataFreshness" in resp
    assert "3) Backtest" in resp
    assert "4) StrategyPool+Leaderboard" in resp
    assert "5) Governance(Overfit)" in resp
    assert "6) Guardrails" in resp
    assert "狀態:" in resp
    assert "白話:" in resp
    assert "下一步:" in resp
    assert "SSOT(" in resp
    assert "MDD(" in resp
    assert "DCA(" in resp
    assert "RegimeSignal（市場風險告警）=FAIL" in resp
    assert "來源=reports/strategy_research/phase3/phase3_results.json" in resp
    assert "版本=abc123def456" in resp
    assert "校準狀態=STALE" in resp
    assert "上次校準=2026-02-18T00:00:00Z" in resp
    assert "先降槓桿或降部位、暫停 promote" in resp
    assert "SHORT覆蓋" in resp
    assert "來源：LOCAL trend_mvp_btc_1h__long__baseline（worker 較舊，沿用 local）" in resp
    assert "RefreshHint: bash scripts/refresh_state.sh" in resp


def test_daily_command_regime_calibration_stale_sop(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_daily_report_ssot(repo)
    monkeypatch.setattr(s, "REPO", repo)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: None)

    # Override fixture to simulate calibration stale with no immediate fail.
    state_dir = repo / "data/state"
    payload = json.loads((state_dir / "daily_report_latest.json").read_text(encoding="utf-8"))
    payload["ssot_components"]["regime_signal"]["status"] = "OK"
    payload["ssot_components"]["regime_signal"]["top_reason"] = "within range"
    payload["ssot_components"]["regime_signal"]["calibration_status"] = "STALE"
    payload["ssot_components"]["regime_signal"]["last_calibrated_utc"] = "2026-02-01T00:00:00Z"
    (state_dir / "daily_report_latest.json").write_text(json.dumps(payload), encoding="utf-8")

    resp = s._handle_command(381, "/daily")
    assert "校準狀態=STALE" in resp
    assert "Regime 門檻校準已過期；先跑 calibrate_regime_thresholds 並開 policy PR" in resp


def test_daily_command_section_shape_is_three_lines(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_daily_report_ssot(repo)
    monkeypatch.setattr(s, "REPO", repo)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: None)

    resp = s._handle_command(380, "/daily")
    for idx, title in [
        (1, "SystemHealth"),
        (2, "DataFreshness"),
        (3, "Backtest"),
        (4, "StrategyPool+Leaderboard"),
        (5, "Governance(Overfit)"),
        (6, "Guardrails"),
    ]:
        anchor = f"{idx}) {title}"
        assert anchor in resp
        after = resp.split(anchor, 1)[1]
        lines = [ln for ln in after.splitlines() if ln.strip()]
        assert lines[0].startswith("狀態:")
        if title == "Backtest":
            assert lines[1].startswith("來源：")
            assert lines[2].startswith("白話:")
            assert lines[3].startswith("下一步:")
        else:
            assert lines[1].startswith("白話:")
            assert lines[2].startswith("下一步:")


def test_daily_command_backtest_worker_source_line(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    _write_daily_report_ssot(repo)
    monkeypatch.setattr(s, "REPO", repo)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: None)

    state_dir = repo / "data/state"
    payload = json.loads((state_dir / "daily_report_latest.json").read_text(encoding="utf-8"))
    payload["latest_backtest_head"]["source"] = "worker_inbox"
    payload["latest_backtest_head"]["bundle"] = "mba_m4_backtests_20260228T083052Z"
    payload["latest_backtest_head"]["reason"] = "worker bundle newer than local backtest"
    payload["sources"]["worker_inbox"]["note"] = "worker 較新，已選為最新回測"
    (state_dir / "daily_report_latest.json").write_text(json.dumps(payload), encoding="utf-8")

    resp = s._handle_command(382, "/daily")
    assert "來源：WORKER mba_m4_backtests_20260228T083052Z" in resp


def test_daily_command_missing_ssot(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: None)

    resp = s._handle_command(39, "/daily")
    assert "DAILY_REPORT_STATUS: WARN" in resp
    assert "missing_daily_report_ssot" in resp
    assert "資料不足/UNKNOWN" in resp
    assert "6) Guardrails" in resp
    assert "RefreshHint: bash scripts/refresh_state.sh" in resp


def test_report_daily_alias_not_supported(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    resp = s._handle_command(39, "/report_daily")
    assert "不認識" in resp


def test_ping_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(40, "/ping")
    assert resp == "pong ✅"


def test_skill_status_overview_reuses_status_report(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    monkeypatch.setattr(
        s,
        "_status_short_report",
        lambda: "SSOT_STATUS: OK\nFreshness: OK\nSources: a.json, b.json",
    )

    def _unexpected_snapshot():
        raise AssertionError("status_overview should not call _collect_snapshot")

    monkeypatch.setattr(s, "_collect_snapshot", _unexpected_snapshot)

    without_sources = s.skill_status_overview(include_sources=False)
    with_sources = s.skill_status_overview(include_sources=True)

    assert "SSOT_STATUS: OK" in without_sources
    assert "Sources:" not in without_sources
    assert "Sources: a.json, b.json" in with_sources


def test_skills_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(50, "/skills")
    assert "status_overview" in resp
    assert "logs_tail_hint" in resp
    assert "rag_search" in resp
    assert "signal_leakage_and_lookahead_audit" in resp
    assert "incident_timeline_builder" in resp


def test_rag_search_run_accepts_quoted_query(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    db_dir = repo / "_local" / "lancedb" / "hongstr_obsidian.lancedb"

    from scripts.obsidian_common import save_index_rows

    save_index_rows(
        db_dir,
        [
            {
                "id": "chunk-1",
                "vault_rel_path": "Daily/2026/03/2026-03-02.md",
                "heading_path": "Daily/2026/03/2026-03-02.md#Summary",
                "chunk_text": "Freshness status is WARN and the ETL backlog needs review.",
                "chunk_hash": "hash-1",
                "created_utc": "2026-03-02T10:00:00Z",
                "metadata": {"type": "daily", "date": "2026-03-02"},
                "embedding": [],
            }
        ],
        provider_name="ollama",
        ollama_model="nomic-embed-text",
    )
    monkeypatch.setattr(s, "REPO", repo)

    out, ok = s._handle_run('/run rag_search query="freshness status" k=5')
    assert ok is True
    payload = json.loads(out)
    assert payload["status"] == "OK"
    assert payload["chunks"]
    assert payload["chunks"][0]["pointer"] == "Daily/2026/03/2026-03-02.md#Summary"


def test_incident_timeline_builder_run_from_health_pack(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "REPO", INCIDENT_FIXTURES / "with_health_pack")

    out, ok = s._handle_run(
        "/run incident_timeline_builder "
        "start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod "
        "keywords=latency,regime services=tg_cp,dashboard"
    )
    assert ok is True
    payload = json.loads(out)
    assert set(payload.keys()) == {"summary", "timeline", "suspected_root_causes", "next_questions"}
    assert payload["summary"]["report_only"] is True
    assert payload["summary"]["status"] in {"OK", "WARN", "FAIL", "UNKNOWN"}
    assert isinstance(payload["timeline"], list) and payload["timeline"]


def test_incident_timeline_builder_run_missing_ssot_returns_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "REPO", INCIDENT_FIXTURES / "missing_all")

    out, ok = s._handle_run(
        "/run incident_timeline_builder start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload["summary"]["status"] == "UNKNOWN"
    assert payload["summary"]["status"] == "UNKNOWN"
    assert "refresh_state.sh" in str(payload["summary"]["refresh_hint"])


def test_incident_timeline_builder_run_fallback_only(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "REPO", INCIDENT_FIXTURES / "fallback_only")

    out, ok = s._handle_run(
        "/run incident_timeline_builder "
        "start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload["summary"]["status"] in {"OK", "WARN"}
    assert payload["summary"]["source_mode"] == "ssot_fallback"
    assert len(payload["timeline"]) >= 4  # 4 component files


def test_incident_timeline_builder_run_unreadable_ssot_returns_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    # Corrupt JSON
    (state_dir / "system_health_latest.json").write_text("{corrupt", encoding="utf-8")
    monkeypatch.setattr(s, "REPO", repo)

    out, ok = s._handle_run(
        "/run incident_timeline_builder start=2026-02-26T00:00:00Z end=2026-02-26T06:00:00Z env=prod"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload["summary"]["status"] == "UNKNOWN"
    assert "freshness_table.json: missing" in str(payload["suspected_root_causes"])


def test_unknown_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(60, "/foobar")
    assert "/help" in resp


def test_signal_leakage_lookahead_proxy_skill(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    out, ok = s._handle_run(
        "/run signal_leakage_and_lookahead_audit artifact_path=research/audit/tests/fixtures/lookahead.json"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload.get("report_only") is True
    assert payload.get("status") == "FAIL"
    assert any(i.get("type") == "lookahead" for i in payload.get("issues", []))


def test_signal_leakage_lookahead_proxy_scope_guard(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    out, ok = s._handle_run(
        "/run signal_leakage_and_lookahead_audit artifact_path=data/state/system_health_latest.json"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload.get("status") == "UNKNOWN"
    assert any(i.get("type") == "scope" for i in payload.get("issues", []))


# ── conversation history ──

def test_history_accumulates(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    state = s._load_session_state()
    assert s._get_history(state, 100) == []

    s._append_history(state, 100, "user", "hello")
    s._append_history(state, 100, "assistant", "hi there")
    s._save_session_state(state)

    state2 = s._load_session_state()
    history = s._get_history(state2, 100)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_history_trims_to_max(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "HISTORY_MAX_TURNS", 3)

    state = s._load_session_state()
    for i in range(10):
        s._append_history(state, 200, "user", f"msg-{i}")
        s._append_history(state, 200, "assistant", f"reply-{i}")
    s._save_session_state(state)

    state2 = s._load_session_state()
    history = s._get_history(state2, 200)
    assert len(history) <= 6  # 3 turns * 2 messages


# ── system prompt ──

def test_system_prompt_includes_snapshot(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    prompt = s._build_system_prompt()
    assert "系統快照" in prompt
    assert "read-only" in prompt or "唯讀" in prompt or "硬圍欄" in prompt


def test_system_prompt_includes_user_memories(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    # write a memory
    s._write_user_memory(300, "以後叫我洪老爺")

    prompt = s._build_system_prompt()
    assert "洪老爺" in prompt


def test_prompt_pack_overlay_selection():
    assert select_overlay("qwen2.5-coder:7b-instruct") == "overlay_qwen2.5-coder_7b_instruct.md"
    assert select_overlay("deepseek-r1:7b") == "overlay_deepseek-r1_7b.md"
    assert select_overlay("qwen2.5:7b-instruct") == "overlay_qwen2.5_7b_instruct.md"
    assert select_overlay("unknown-model") == "overlay_qwen2.5_7b_instruct.md"


def test_prompt_pack_builds_for_supported_models():
    for model_name in ("qwen2.5-coder:7b-instruct", "deepseek-r1:7b", "qwen2.5:7b-instruct"):
        prompt = build_prompt_pack_system_prompt(model_name)
        assert prompt
        assert "HARD RED LINES" in prompt


# ── secret redaction ──

def test_reply_does_not_leak_token():
    from _local.telegram_cp.guardrail import redact_secrets
    text = "token is bot123456:ABCDefGHIjklmnOP_qrstuvwxyz"
    cleaned = redact_secrets(text)
    assert "bot123456" not in cleaned
    assert "<REDACTED>" in cleaned


# ── LLM offline fallback ──

def test_llm_offline_returns_fallback(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp, route = s.build_chat_reply(400, "你好", use_llm=False)
    assert route == "FALLBACK"
    assert "LLM" in resp or "/status" in resp or "/help" in resp


# ── remember command ──

def test_remember_and_memories(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    resp = s._handle_command(500, "/remember 以後叫我洪老爺")
    assert "記" in resp

    resp2 = s._handle_command(500, "/memories")
    assert "洪老爺" in resp2


# ── deferred followup queue ──

def test_extract_followup_tag_basic():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "好的，我幫你查，等等回報你。\n[FOLLOWUP:5:ETL 狀態和資料新鮮度]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes == 5
    assert "ETL" in topic
    assert "[FOLLOWUP" not in cleaned


def test_extract_followup_tag_none():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "系統目前看起來正常。"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes is None
    assert topic is None
    assert cleaned == text


def test_extract_followup_tag_spaced():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    text = "馬上為您處理。\n[ FOLLOWUP : 2 : ETL 狀態和資料新鮮度 ]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes == 2
    assert "ETL" in topic
    assert "[ FOLLOWUP" not in cleaned


def test_extract_followup_tag_clamp():
    from _local.telegram_cp.tg_cp_server import _extract_followup_tag
    # 999 minutes should be clamped to FOLLOWUP_MAX_DELAY_MIN (default 60)
    text = "等等告訴你。\n[FOLLOWUP:999:CPU 狀態]"
    minutes, topic, cleaned = _extract_followup_tag(text)
    assert minutes is not None
    assert minutes <= 60


def test_enqueue_and_load_followup(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    s._enqueue_followup(100, 5, "ETL 狀態", "ETL 好了嗎")

    due = s._load_due_followups()
    assert len(due) == 0  # not due yet (due_at = now + 5 min)

    # Manually back-date it
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    records = [json.loads(l) for l in lines if l.strip()]
    records[0]["due_at"] = 1  # epoch 1 = far in the past
    s.FOLLOWUP_QUEUE.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
    )

    due = s._load_due_followups()
    assert len(due) == 1
    assert due[0]["topic"] == "ETL 狀態"


def test_mark_followups_done(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    s._enqueue_followup(200, 1, "測試主題", "msg")
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    fid = json.loads(lines[0])["id"]

    s._mark_followups_done([fid])

    lines2 = s.FOLLOWUP_QUEUE.read_text().splitlines()
    assert json.loads(lines2[0])["done"] is True


def test_build_chat_reply_enqueues_followup(monkeypatch, tmp_path):
    """build_chat_reply strips FOLLOWUP tag and enqueues the task."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    monkeypatch.setattr(s, "FOLLOWUP_ENABLED", True)

    # Mock LLM to return a response with a FOLLOWUP tag
    def fake_llm(chat_id, user_text, history):
        return "好的，等一下回報你。\n[FOLLOWUP:3:ETL 資料新鮮度]", None
    monkeypatch.setattr(s, "_llm_chat", fake_llm)

    resp, route = s.build_chat_reply(600, "ETL 好了嗎")
    assert route == "LLM"
    assert "[FOLLOWUP" not in resp  # tag stripped from visible reply
    assert "好的" in resp

    # Queue should have one entry
    import json
    lines = s.FOLLOWUP_QUEUE.read_text().splitlines()
    assert len(lines) == 1
    task = json.loads(lines[0])
    assert task["topic"] == "ETL 資料新鮮度"
    assert task["done"] is False
    assert task["chat_id"] == 600
    assert task["chat_id"] == 600


def test_build_chat_reply_executes_rag_search_tool_call(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    fake_snap = {
        "dashboard_ok": True,
        "regime_monitor": {"status": "OK"},
        "freshness": {},
        "cp_status": "OK",
        "overall_gate": "OK",
        "cp_age_hours": 1.0,
        "cp_summary": "Summary",
        "top_action": "None",
        "pending_alerts": 0,
        "etl_ok": True,
        "etl_fail": False,
        "log_ages": {"etl": 1.0, "healthcheck": 1.0},
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    calls = []

    def fake_llm(chat_id, user_text, history):
        calls.append(user_text)
        if len(calls) == 1:
            return ('{"tool":"rag_search","args":{"query":"freshness status","k":5}}', None)
        assert "Tool `rag_search` result" in user_text
        return ("Freshness is WARN. See Daily/2026/03/2026-03-02.md#Summary", None)

    monkeypatch.setattr(s, "_llm_chat", fake_llm)
    monkeypatch.setattr(
        s,
        "_execute_llm_tool_call",
        lambda *args, **kwargs: {
            "status": "OK",
            "provider": "lancedb",
            "db_path": "_local/lancedb/hongstr_obsidian.lancedb",
            "chunks": [
                {
                    "pointer": "Daily/2026/03/2026-03-02.md#Summary",
                    "text": "Freshness status is WARN.",
                    "score": 3.0,
                    "metadata": {"type": "daily"},
                }
            ],
        },
    )

    resp, route = s.build_chat_reply(601, "請先查 freshness status 再回答")
    assert route == "LLM_TOOL"
    assert "Daily/2026/03/2026-03-02.md#Summary" in resp


# ── freshness ──

def test_evaluate_freshness_boundaries():
    from _local.telegram_cp.tg_cp_server import _evaluate_freshness
    
    # OK: <= 12h
    assert _evaluate_freshness(0.0)[0] == "OK"
    assert _evaluate_freshness(12.0)[0] == "OK"
    
    # WARN: 12 < age <= 48
    assert _evaluate_freshness(12.1)[0] == "WARN"
    assert "exceeds 12h" in _evaluate_freshness(12.1)[1]
    assert _evaluate_freshness(48.0)[0] == "WARN"
    
    # FAIL: > 48
    assert _evaluate_freshness(48.1)[0] == "FAIL"
    assert "exceeds 48h" in _evaluate_freshness(48.1)[1]
    
    # None: WARN (missing file)
    assert _evaluate_freshness(None)[0] == "WARN"
    assert "missing" in _evaluate_freshness(None)[1]


def test_snapshot_text_freshness_logic(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    fake_snap = {
        "status_report": "SSOT_STATUS: OK\nFreshness: OK max_age_h=1.0\nRegimeSignal: FAIL (MDD breach)",
        "refresh_hint": "bash scripts/refresh_state.sh",
        "pending_alerts": 2,
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)

    text = s._snapshot_text()
    assert "[系統快照 " in text
    assert "SSOT_STATUS: OK" in text
    assert "RegimeSignal: FAIL (MDD breach)" in text
    assert "RefreshHint: Run `bash scripts/refresh_state.sh` when SSOT snapshots are missing or stale." in text
    assert "待處理排程告警: 2 筆" in text
    # Legacy dynamic/log-derived summary should not appear in the SSOT-only snapshot text.
    assert "Dashboard:" not in text
    assert "Backtest Gate:" not in text


def test_freshness_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock snapshot with a known state
    fake_snap = {
        "freshness": {
            "BTCUSDT": {
                "1m": {"age_hours": 1.0, "status": "OK"},
                "1h": {"age_hours": 2.0, "status": "OK"},
                "4h": {"age_hours": 3.0, "status": "OK"},
            },
            "ETHUSDT": {
                "1m": {"age_hours": 15.0, "status": "WARN"},
                "1h": {"age_hours": 0.5, "status": "OK"},
                "4h": {"age_hours": 0.5, "status": "OK"},
            },
            "BNBUSDT": {
                "1m": {"age_hours": 50.0, "status": "FAIL"},
                "1h": {"age_hours": 0.5, "status": "OK"},
                "4h": {"age_hours": 0.5, "status": "OK"},
            }
        }
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    resp = s._handle_command(12345, "/freshness")
    assert "完整報表" in resp
    assert "BTCUSDT: 1m: 1.0h (OK)" in resp
    assert "ETHUSDT: 1m: 15.0h (WARN)" in resp
    assert "BNBUSDT: 1m: 50.0h (FAIL)" in resp
    # check disclaimer
    assert "唯讀" in resp
    assert "下單" in resp


def test_freshness_sop_guidance(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Case: WARN should trigger SOP guidance
    fake_snap = {
        "freshness": {
            "BTCUSDT": {
                "1m": {"age_hours": 20.0, "status": "WARN"},
                "1h": {"age_hours": 0.0, "status": "OK"},
                "4h": {"age_hours": 0.0, "status": "OK"},
            }
        }
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    resp = s._handle_command(12345, "/freshness")
    assert "自修引導" in resp
    assert "check_data_coverage.sh" in resp
    assert "保持冷靜" in resp
    assert "🔴" not in resp  # No FAIL yet

    # Case: FAIL should trigger senior guidance
    fake_snap["freshness"]["BTCUSDT"]["1m"] = {"age_hours": 50.0, "status": "FAIL"}
    resp = s._handle_command(12345, "/freshness")
    assert "🔴" in resp
    assert "人工介入" in resp


def test_ml_status_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock REPO
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    
    # Case: Missing files
    resp = s._handle_command(12345, "/ml_status")
    assert "異常" in resp
    assert "Evidence Summary: ❌ 缺失" in resp
    assert "ML Signals: ❌ 缺失" in resp
    assert "ml_daily_manual.sh" in resp

    # Case: Files exist (mocking pandas len)
    evidence_dir = repo / "reports/research/ml"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "evidence_summary.json").write_text("{}")
    
    signal_dir = repo / "reports/research/signals"
    signal_dir.mkdir(parents=True)
    signal_file = signal_dir / "signal_1h_24.parquet"
    signal_file.write_text("fake parquet data")
    
    # Mock pandas.read_parquet to avoid actual parquet parsing
    class FakePD:
        @staticmethod
        def read_parquet(path):
            return [1, 2, 3] # len=3
    monkeypatch.setitem(sys.modules, "pandas", FakePD)
    
    resp = s._handle_command(12345, "/ml_status")
    assert "正常" in resp
    assert "Evidence Summary: ✅" in resp
    assert "ML Signals: ✅ 存在 (3 rows)" in resp


def test_regime_command(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock REPO
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    latest_p = state_dir / "regime_monitor_latest.json"
    
    # Case: Missing file
    resp = s._handle_command(12345, "/regime")
    assert "UNKNOWN" in resp
    assert "尚未產生快照" in resp

    # Case: OK
    fake_snap = {
        "freshness": {
            "BTCUSDT": {"1m": {"status": "OK"}, "1h": {"status": "OK"}, "4h": {"status": "OK"}}
        },
        "regime_monitor": {
            "overall": "OK",
            "ts_utc": "2026-02-24T00:00:00Z",
            "current": {
                "sharpe": 1.5, 
                "mdd": -0.02, 
                "trades": 100, 
                "summary_path": "data/backtests/run1/summary.json",
                "source_reason": "full_run"
            },
            "reason": ["All metrics within comfort zone"]
        }
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    resp = s._handle_command(12345, "/regime")
    assert "OK" in resp
    assert "Sharpe: 1.500" in resp
    assert "來源: `data/backtests/run1/summary.json` (full_run)" in resp
    assert "排除資料缺口" in resp
    assert "資料缺口可能性低" in resp

    # Case: WARN
    fake_snap["regime_monitor"] = {
        "overall": "WARN",
        "ts_utc": "2026-02-24T00:01:00Z",
        "current": {
            "sharpe": 0.3, 
            "mdd": -0.04, 
            "trades": 80, 
            "summary_path": "data/backtests/run2/summary.json",
            "source_reason": "fallback_fragment"
        },
        "reason": ["Sharpe dropped below median"]
    }
    resp = s._handle_command(12345, "/regime")
    assert "WARN" in resp
    assert "來源: `data/backtests/run2/summary.json` (fallback_fragment)" in resp
    assert "下一步檢查順序" in resp
    assert "check_data_coverage.sh" in resp

# ── Specialist Routing ──

def test_specialist_routing_via_keyword(monkeypatch, tmp_path):
    """Test that 'why' triggers the Reasoning Specialist."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock snapshot
    fake_snap = {
        "dashboard_ok": True,
        "regime_monitor": {"status": "OK"},
        "freshness": {}, 
        "cp_status": "OK",
        "cp_age_hours": 1.0,
        "cp_summary": "Summary",
        "overall_gate": "OK",
        "top_action": "None",
        "pending_alerts": 0,
        "etl_ok": True,
        "etl_fail": False,
        "log_ages": {"etl": 1.0, "healthcheck": 1.0}
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    # Mock specialist call
    mock_analysis = ReasoningAnalysis(
        status="OK",
        problem="Test Problem",
        key_findings=["Finding 1"],
        hypotheses=["Hypothesis 1"],
        recommended_next_steps=["Step 1"],
        risks=[],
        citations=[]
    )
    
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: mock_analysis)
    
    resp, route = s.build_chat_reply(100, "Why is the system behaving like this?")
    assert route == "SPECIALIST"
    assert "Reasoning Specialist" in resp or "Reasoning Specialist Analysis" in resp
    assert "Test Problem" in resp

def test_specialist_routing_via_state_trigger(monkeypatch, tmp_path):
    """Test that Regime FAIL triggers the Reasoning Specialist for status queries."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock snapshot with Regime FAIL
    fake_snap = {
        "dashboard_ok": True,
        "regime_monitor": {"status": "FAIL"},
        "freshness": {},
        "cp_status": "WARN",
        "overall_gate": "FAIL",
        "pending_alerts": 5,
        "cp_age_hours": 1.0,
        "cp_summary": "Summary",
        "top_action": "Fix Regime",
        "etl_ok": True,
        "etl_fail": False,
        "log_ages": {"etl": 1.0, "healthcheck": 1.0}
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    # Mock specialist call
    mock_analysis = ReasoningAnalysis(
        status="FAIL",
        problem="Regime Failure",
        key_findings=["Regime is broken"],
        hypotheses=["Market volatility"],
        recommended_next_steps=["Check data"],
        risks=[],
        citations=[]
    )
    
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: mock_analysis)
    
    resp, route = s.build_chat_reply(101, "目前的狀態如何？") # "status" keyword in Chinese
    assert route == "SPECIALIST"
    assert "Regime Failure" in resp

def test_specialist_fallback_to_broker(monkeypatch, tmp_path):
    """Test that Broker is used if Specialist fails."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Trigger with 'why'
    fake_snap = {
        "dashboard_ok": True,
        "regime_monitor": {"status": "OK"},
        "freshness": {},
        "cp_status": "OK",
        "overall_gate": "OK",
        "cp_age_hours": 1.0,
        "cp_summary": "Summary",
        "top_action": "None",
        "pending_alerts": 0,
        "etl_ok": True,
        "etl_fail": False,
        "log_ages": {"etl": 1.0, "healthcheck": 1.0}
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    # Mock specialist failure (returns None)
    monkeypatch.setattr(s, "call_reasoning_specialist", lambda *args, **kwargs: None)
    # Mock broker chat
    monkeypatch.setattr(s, "_llm_chat", lambda *args, **kwargs: ("Broker reply", None))
    
    resp, route = s.build_chat_reply(102, "Why?")
    assert route == "FALLBACK_WARN" 
    assert "Timeout/Fail" in resp

def test_regime_warn_freshness_ok(monkeypatch, tmp_path):
    """Test Regime WARN + Freshness OK -> Data gap unlikely."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    fake_snap = {
        "freshness": {
            "BTCUSDT": {"1m": {"status": "OK"}, "1h": {"status": "OK"}, "4h": {"status": "OK"}}
        },
        "regime_monitor": {
            "overall": "WARN",
            "ts_utc": "2026-02-24T03:29:34Z",
            "reason": ["MDD elevated"],
            "current": {
                "sharpe": 0.2,
                "mdd": -0.033,
                "trades": 800,
                "summary_source": "data/backtests/summary.json"
            }
        }
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    out = s.skill_regime_status()
    assert "結論: WARN" in out
    assert "資料缺口可能性低" in out
    assert "1. 查看 regime 源文件" in out
    assert "scripts/check_data_coverage.sh" in out

def test_regime_warn_freshness_fail(monkeypatch, tmp_path):
    """Test Regime WARN + Freshness FAIL -> Recommend ETL first."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    fake_snap = {
        "freshness": {
            "BTCUSDT": {"1m": {"status": "FAIL"}, "1h": {"status": "OK"}, "4h": {"status": "OK"}},
            "ETHUSDT": {"1m": {"status": "OK"}, "1h": {"status": "OK"}, "4h": {"status": "OK"}},
            "BNBUSDT": {"1m": {"status": "OK"}, "1h": {"status": "OK"}, "4h": {"status": "OK"}}
        },
        "regime_monitor": {
            "overall": "WARN",
            "ts_utc": "2026-02-24T03:29:34Z",
            "reason": ["MDD elevated"],
            "current": {
                "sharpe": 0.2,
                "mdd": -0.033,
                "trades": 800,
                "summary_source": "data/backtests/summary.json"
            }
        }
    }
    monkeypatch.setattr(s, "_collect_snapshot", lambda: fake_snap)
    
    out = s.skill_regime_status()
    assert "結論: WARN" in out
    assert "偵測到資料過時" in out
    assert "1. 執行 `bash scripts/check_data_coverage.sh`" in out

# ── specialist parser robustness ──

def test_specialist_parser_prose(monkeypatch, tmp_path):
    """Test parser with text prose around JSON."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock Ollama response with prose
    prose_content = "Here is my analysis:\n{\"status\": \"OK\", \"problem\": \"p\", \"key_findings\": [], \"hypotheses\": [], \"recommended_next_steps\": [], \"risks\": [], \"actions\": [], \"citations\": []}\nHope this helps!"
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"message": {"content": prose_content}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_resp)
    
    # Trigger specialist
    resp, route = s.build_chat_reply(200, "Why is the system behaving like this?")
    assert route == "SPECIALIST"
    assert "OK" in resp

def test_specialist_parser_codefence(monkeypatch, tmp_path):
    """Test parser with markdown codefence."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock Ollama response with codefence
    code_content = "<thought>Thinking...</thought>\n```json\n{\"status\": \"WARN\", \"problem\": \"p2\", \"key_findings\": [], \"hypotheses\": [], \"recommended_next_steps\": [], \"risks\": [], \"actions\": [], \"citations\": []}\n```"
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"message": {"content": code_content}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_resp)
    
    # Trigger specialist
    resp, route = s.build_chat_reply(201, "Why?")
    assert route == "SPECIALIST"
    assert "WARN" in resp
    assert "p2" in resp

def test_specialist_parser_double_json_uses_first(monkeypatch, tmp_path):
    """Test parser extracts first JSON object when multiple objects appear."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)

    double_content = (
        "{\"status\": \"OK\", \"problem\": \"first\", \"key_findings\": [], \"hypotheses\": [], "
        "\"recommended_next_steps\": [], \"risks\": [], \"actions\": [], \"citations\": []}\n"
        "{\"status\": \"FAIL\", \"problem\": \"second\", \"key_findings\": [], \"hypotheses\": [], "
        "\"recommended_next_steps\": [], \"risks\": [], \"actions\": [], \"citations\": []}"
    )
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"message": {"content": double_content}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_resp)

    resp, route = s.build_chat_reply(207, "Why?")
    assert route == "SPECIALIST"
    assert "OK" in resp
    assert "first" in resp
    assert "second" not in resp

def test_specialist_parser_unparsable(monkeypatch, tmp_path):
    """Test fallback to WARN when content is completely unparsable."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock Ollama response with garbage
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"message": {"content": "I am a potato and I refuse to speak JSON."}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_resp)
    
    # Trigger specialist
    resp, route = s.build_chat_reply(202, "Why?")
    assert route == "SPECIALIST"
    assert "WARN" in resp
    assert "failed" in resp or "invalid" in resp
    assert "refresh_state.sh" in resp

def test_specialist_parser_schema_normalization(monkeypatch, tmp_path):
    """Test schema normalization (missing status/actions)."""
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    
    # Mock Ollama response with missing status and actions
    minimal_json = "{\"problem\": \"missing fields\", \"key_findings\": [], \"hypotheses\": [], \"recommended_next_steps\": [], \"risks\": [], \"citations\": []}"
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"message": {"content": minimal_json}}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: mock_resp)
    
    # Trigger specialist
    resp, route = s.build_chat_reply(203, "Why?")
    assert route == "SPECIALIST"
    assert "WARN" in resp
    assert "missing fields" in resp

# ── system_health_morning_brief ──

def test_morning_brief_full_pack(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    
    # Use fixture content
    fixture_path = FIXTURES_DIR / "health_brief" / "system_health_latest_ok.json"
    (state_dir / "system_health_latest.json").write_text(fixture_path.read_text())
    
    monkeypatch.setattr(s, "REPO", repo)
    
    # Test via skill implementation directly
    from _local.telegram_cp.skills.system_health_morning_brief import get_morning_brief
    res = get_morning_brief(repo, "prod", include_details=True)
    
    assert res["status"] == "OK"
    assert "Morning Brief" in res["markdown"]
    assert "Coverage: OK" in res["markdown"]
    assert "source_mode': 'system_health_latest" in str(res["data"])

def test_morning_brief_fallback(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    
    # Write component files only
    (state_dir / "freshness_table.json").write_text(json.dumps({"rows": [{"status": "OK"}]}))
    (state_dir / "coverage_matrix_latest.json").write_text(json.dumps({"totals": {"status": "PASS"}}))
    (state_dir / "brake_health_latest.json").write_text(json.dumps({"status": "OK"}))
    (state_dir / "regime_monitor_latest.json").write_text(json.dumps({"status": "OK"}))
    
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.system_health_morning_brief import get_morning_brief
    res = get_morning_brief(repo, "prod")
    
    assert res["status"] == "OK"
    assert "Fallback" in res["markdown"]
    assert "source_mode': 'ssot_fallback" in str(res["data"])

def test_morning_brief_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.system_health_morning_brief import get_morning_brief
    res = get_morning_brief(repo, "prod")
    
    assert res["status"] == "UNKNOWN"
    assert "Issues: Missing" in res["markdown"]

def test_morning_brief_integration(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    (state_dir / "system_health_latest.json").write_text(json.dumps({
        "ssot_status": "OK",
        "components": {"coverage_matrix": {"status": "PASS"}}
    }))
    monkeypatch.setattr(s, "REPO", repo)
    
    # Test via /run command
    out, ok = s._handle_run("/run system_health_morning_brief env=prod")
    assert ok is True
    assert "Morning Brief" in out
    assert "Status: OK" in out

# ── config_drift_auditor ──

def test_config_drift_auditor_no_drift(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / ".env.example").write_text("BASE=1\n", encoding="utf-8")
    monkeypatch.setattr(s, "REPO", repo_path)

    # Mock git.Repo
    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_blob = MagicMock()
    mock_blob.data_stream.read.return_value = b"BASE=1\n"
    
    # Using __truediv__ for path lookup in tree
    mock_commit.tree.__truediv__.return_value = mock_blob
    mock_repo.commit.return_value = mock_commit
    
    with patch("git.Repo", return_value=mock_repo):
        from _local.telegram_cp.skills.config_drift_auditor import audit_config_drift
        res = audit_config_drift(repo_path, "baseline_sha", paths=".env.example")
        
    assert res["status"] == "OK"
    assert "No drift detected" in res["markdown"]
    assert len(res["data"]["results"]) == 1
    assert res["data"]["results"][0]["status"] == "MATCH"

def test_config_drift_auditor_with_drift(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    (repo_path / ".env.example").write_text("CURRENT=2\n", encoding="utf-8")
    monkeypatch.setattr(s, "REPO", repo_path)

    mock_repo = MagicMock()
    mock_commit = MagicMock()
    mock_blob = MagicMock()
    mock_blob.data_stream.read.return_value = b"BASE=1\n"
    
    mock_commit.tree.__truediv__.return_value = mock_blob
    mock_repo.commit.return_value = mock_commit
    
    with patch("git.Repo", return_value=mock_repo):
        from _local.telegram_cp.skills.config_drift_auditor import audit_config_drift
        res = audit_config_drift(repo_path, "baseline_sha", paths=".env.example")
        
    assert res["status"] == "WARN"
    assert "Drifted" in res["markdown"]
    assert res["data"]["results"][0]["status"] == "DRIFT"
    assert "diff" in res["data"]["results"][0]

def test_config_drift_auditor_unknown_ref(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    monkeypatch.setattr(s, "REPO", repo_path)

    mock_repo = MagicMock()
    mock_repo.commit.side_effect = Exception("not found")
    
    with patch("git.Repo", return_value=mock_repo):
        from _local.telegram_cp.skills.config_drift_auditor import audit_config_drift
        res = audit_config_drift(repo_path, "missing_sha")
        
    assert res["status"] == "UNKNOWN"
    assert "not found" in res["markdown"]

# ── data_freshness_watchdog_report ──

def test_freshness_report_full_pack(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    
    (state_dir / "system_health_latest.json").write_text(json.dumps({
        "generated_utc": "2026-02-26T12:00:00Z",
        "components": {
            "freshness": {"status": "OK", "max_age_h": 0.5}
        }
    }))
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.data_freshness_watchdog_report import get_freshness_report
    res = get_freshness_report(repo, "prod")
    
    assert res["status"] == "OK"
    assert "Watchdog" in res["markdown"]
    assert "Max Gap:* 0.5h" in res["markdown"]
    assert res["data"]["source_mode"] == "system_health_latest"

def test_freshness_report_fallback(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    state_dir = repo / "data/state"
    state_dir.mkdir(parents=True)
    
    (state_dir / "freshness_table.json").write_text(json.dumps({
        "ts_utc": "2026-02-26T12:00:00Z",
        "rows": [
            {"symbol": "BTCUSDT", "tf": "1m", "status": "OK", "age_h": 0.1},
            {"symbol": "ETHUSDT", "tf": "1m", "status": "WARN", "age_h": 1.5}
        ]
    }))
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.data_freshness_watchdog_report import get_freshness_report
    res = get_freshness_report(repo, "prod")
    
    assert res["status"] == "WARN"
    assert "Max Gap:* 1.5h" in res["markdown"]
    assert res["data"]["source_mode"] == "ssot_fallback"

def test_freshness_report_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.data_freshness_watchdog_report import get_freshness_report
    res = get_freshness_report(repo, "prod")
    
    assert res["status"] == "UNKNOWN"
    assert "No freshness data found" in res["markdown"]

# ── execution_quality_report_readonly ──

def test_execution_quality_report_missing_ssot_returns_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    # No execution_quality_latest.json created
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.execution_quality_report_readonly import get_execution_quality_report
    res = get_execution_quality_report(repo, "prod")
    
    assert res["status"] == "UNKNOWN"
    assert "Execution Quality SSOT missing" in res["markdown"]
    assert "data/state/execution_quality_latest.json" in res["markdown"]

# ── Quant Specialist Skeletons (B1, B2, B5) ──

def test_backtest_reproducibility_audit_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "reports/research").mkdir(parents=True)
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.backtest_reproducibility_audit import audit_backtest_reproducibility
    res = audit_backtest_reproducibility(repo, "BT_123", "sha_xyz")
    
    assert res["status"] in {"UNKNOWN", "WARN"}
    assert res["report_only"] is True
    assert res["actions"] == []
    assert res["missing_artifacts"]
    assert "refresh_state.sh" in str(res.get("refresh_hint", ""))

def test_factor_health_and_drift_report_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "reports/research/factors").mkdir(parents=True)
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.factor_health_and_drift_report import get_factor_health_report
    res = get_factor_health_report(repo, "factor_alpha")
    
    assert res["status"] in {"UNKNOWN", "WARN"}
    assert res["report_only"] is True
    assert res["actions"] == []
    assert res["missing_artifacts"]
    assert "refresh_state.sh" in str(res.get("refresh_hint", ""))

def test_strategy_regime_sensitivity_report_unknown(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "reports/research/sensitivity").mkdir(parents=True)
    monkeypatch.setattr(s, "REPO", repo)
    
    from _local.telegram_cp.skills.strategy_regime_sensitivity_report import get_strategy_sensitivity_report
    res = get_strategy_sensitivity_report(repo, "strat_beta")
    
    assert res["status"] in {"UNKNOWN", "WARN"}
    assert res["report_only"] is True
    assert res["actions"] == []
    assert res["missing_artifacts"]
    assert "refresh_state.sh" in str(res.get("refresh_hint", ""))


def test_run_quant_missing_artifacts_returns_json_contract(monkeypatch, tmp_path):
    s = _load_server()
    _sandbox_state(monkeypatch, tmp_path, s)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(s, "REPO", repo)

    out, ok = s._handle_run(
        "/run backtest_reproducibility_audit backtest_id=BT_123 baseline_sha=sha_xyz"
    )
    assert ok is True
    payload = json.loads(out)
    assert payload["skill"] == "backtest_reproducibility_audit"
    assert payload["status"] in {"WARN", "UNKNOWN"}
    assert payload["report_only"] is True
    assert payload["actions"] == []
    assert payload["missing_artifacts"]
    assert "refresh_state.sh" in str(payload.get("refresh_hint", ""))
