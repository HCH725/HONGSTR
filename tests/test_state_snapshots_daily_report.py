import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/state_snapshots.py"


def _load_state_snapshots_module():
    spec = importlib.util.spec_from_file_location("state_snapshots_daily_testmod", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def test_daily_report_schema_keys_and_types(tmp_path: Path):
    mod = _load_state_snapshots_module()
    report_dir = tmp_path / "reports" / "research" / "20260227" / "cand_a"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "summary.json").write_text(
        json.dumps({"sharpe": 1.2, "max_drawdown": -0.09, "trades_count": 34}),
        encoding="utf-8",
    )
    (report_dir / "gate.json").write_text(
        json.dumps({"overall": "PASS", "final_score": 88.5}),
        encoding="utf-8",
    )
    (report_dir / "selection.json").write_text(json.dumps({"ok": True}), encoding="utf-8")

    payload = mod._build_daily_report_payload(
        now_utc="2026-02-27T00:00:00Z",
        now_ts=1700000000.0,
        system_health={
            "ssot_status": "OK",
            "refresh_hint": "bash scripts/refresh_state.sh",
            "components": {
                "freshness": {"status": "OK"},
                "coverage_matrix": {"status": "PASS"},
                "brake": {"status": "OK"},
                "regime_monitor": {"status": "OK"},
            },
        },
        freshness_table={
            "rows": [
                {"symbol": "BTCUSDT", "tf": "1m", "profile": "realtime", "age_h": 0.2, "status": "OK"},
                {"symbol": "ETHUSDT", "tf": "4h", "profile": "backtest", "age_h": 29.0, "status": "WARN", "reason": "stale"},
            ]
        },
        strategy_pool_summary={
            "counts": {"candidates": 2, "promoted": 1, "demoted": 1},
            "last_updated_utc": "2026-02-27T00:00:00Z",
        },
        strategy_pool_data={
            "report_only": True,
            "candidates": [
                {
                    "strategy_id": "trend_mvp_btc_1h",
                    "candidate_id": "trend_mvp_btc_1h__long__baseline",
                    "family": "trend",
                    "direction": "LONG",
                    "variant": "baseline",
                    "last_score": 77.1,
                    "gate_overall": "PASS",
                    "recommendation": "PROMOTE",
                    "last_oos_metrics": {"sharpe": 1.1, "return": 2.4, "mdd": -0.11},
                }
            ],
        },
        research_leaderboard={
            "generated_at": "2026-02-27T00:00:00Z",
            "top_n": 20,
            "entries": [
                {
                    "candidate_id": "cand_a",
                    "strategy_id": "trend_mvp_btc_1h",
                    "direction": "LONG",
                    "variant": "baseline",
                    "timestamp": "2026-02-27T00:00:00Z",
                    "report_dir": str(report_dir),
                    "gate_overall": "PASS",
                    "final_score": 88.5,
                    "oos_sharpe": 1.2,
                    "oos_mdd": -0.09,
                }
            ],
        },
        loop_state={"actions": []},
        policy_payload={"name": "aggressive_yield_first_v1"},
        repo_root=tmp_path,
    )

    expected_top_keys = {
        "generated_utc",
        "refresh_hint",
        "ssot_status",
        "ssot_components",
        "freshness_summary",
        "latest_backtest_head",
        "strategy_pool",
        "research_leaderboard",
        "governance",
        "guardrails",
        "sources",
    }
    assert expected_top_keys.issubset(set(payload.keys()))
    assert isinstance(payload["generated_utc"], str)
    assert isinstance(payload["ssot_components"], dict)
    assert isinstance(payload["freshness_summary"], dict)
    assert isinstance(payload["strategy_pool"]["leaderboard_top"], list)
    assert isinstance(payload["research_leaderboard"]["top_entries"], list)
    assert isinstance(payload["governance"]["today_gate_summary"], dict)
    assert isinstance(payload["guardrails"]["checks"], dict)
    assert payload["latest_backtest_head"]["gate"]["overall"] in {"PASS", "WARN", "FAIL", "UNKNOWN"}

    top_row = payload["strategy_pool"]["leaderboard_top"][0]
    assert top_row["direction"] == "LONG"
    assert top_row["metrics_status"] in {"OK", "UNKNOWN"}
