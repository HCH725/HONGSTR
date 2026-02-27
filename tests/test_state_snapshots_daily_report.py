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
        json.dumps({"sharpe": 1.2, "max_drawdown": -0.09, "is_sharpe": 1.4, "trades_count": 37}),
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
                "regime_signal": {"status": "WARN"},
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
                    "is_sharpe": 1.4,
                    "trades_count": 37,
                }
            ],
        },
        loop_state={"actions": []},
        policy_payload={"name": "aggressive_yield_first_v1"},
        repo_root=tmp_path,
    )

    assert list(payload.keys()) == mod.DAILY_REPORT_TOP_LEVEL_ORDER
    assert payload["schema"]["version"] == "daily_report.v1"
    assert isinstance(payload["schema"]["field_labels_zh_en"], dict)
    assert "generated_utc" in payload["schema"]["field_labels_zh_en"]

    assert isinstance(payload["freshness_summary"]["profile_totals"], dict)
    assert payload["freshness_summary"]["profile_totals"]["realtime"] == 1
    assert payload["freshness_summary"]["profile_totals"]["backtest"] == 1
    assert payload["latest_backtest_head"]["metrics"]["is_sharpe"] == 1.4
    assert payload["latest_backtest_head"]["metrics"]["trades_count"] == 37

    top_row = payload["strategy_pool"]["leaderboard_top"][0]
    assert top_row["direction"] == "LONG"
    assert top_row["metrics_status"] in {"OK", "UNKNOWN"}
