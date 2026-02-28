from __future__ import annotations

import json
from pathlib import Path

from scripts import state_snapshots as snapshots


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _local_leaderboard(ts_utc: str) -> dict:
    return {
        "entries": [
            {
                "candidate_id": "trend_mvp_btc_1h__long__baseline",
                "strategy_id": "trend_mvp_btc_1h",
                "direction": "LONG",
                "variant": "baseline",
                "status": "SUCCESS",
                "gate_overall": "PASS",
                "final_score": 88.5,
                "oos_sharpe": 1.2,
                "oos_mdd": -0.09,
                "is_sharpe": 1.4,
                "trades_count": 37,
                "timestamp": ts_utc,
                "report_dir": "reports/research/20260228/trend_mvp_btc_1h__long__baseline",
            }
        ]
    }


def _seed_local_report(repo: Path) -> None:
    report_dir = repo / "reports/research/20260228/trend_mvp_btc_1h__long__baseline"
    _write_json(
        report_dir / "summary.json",
        {
            "timestamp": "2026-02-28T08:00:00Z",
            "sharpe": 1.2,
            "max_drawdown": -0.09,
            "is_sharpe": 1.4,
            "trades_count": 37,
            "direction": "LONG",
            "variant": "baseline",
        },
    )
    _write_json(
        report_dir / "gate.json",
        {
            "overall": "PASS",
            "recommendation": "PROMOTE",
        },
    )
    _write_json(report_dir / "selection.json", {"generated_at": "2026-02-28T08:00:00Z"})


def _seed_worker_bundle(repo: Path, bundle_name: str, *, with_summary: bool = True, summary_ts: str = "2026-02-28T08:30:52Z") -> None:
    bundle_dir = repo / "_local/worker_inbox" / bundle_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    if with_summary:
        _write_json(
            bundle_dir / "summary.json",
            {
                "timestamp": summary_ts,
                "sharpe": 0.58,
                "max_drawdown": -0.14,
                "trades_count": 3602,
            },
        )
    _write_json(
        bundle_dir / "selection.json",
        {
            "generated_at": "2026-02-28T08:30:52Z",
            "regime": "BEAR",
        },
    )
    _write_json(
        bundle_dir / "gate.json",
        {
            "generated_at": "2026-02-28T08:30:52Z",
            "inputs": {"mode": "SHORT"},
            "results": {"overall": {"pass": True}},
        },
    )


def test_latest_backtest_head_local_only_when_no_worker(tmp_path: Path):
    repo = tmp_path / "repo"
    _seed_local_report(repo)

    head, worker_meta = snapshots._latest_backtest_head_with_worker_provenance(  # noqa: SLF001
        _local_leaderboard("2026-02-28T08:00:00Z"),
        repo,
    )

    assert head["source"] == "local"
    assert head["timestamp_utc"] == "2026-02-28T08:00:00Z"
    assert worker_meta["present"] is False
    assert worker_meta["ingested_into_state"] is False


def test_latest_backtest_head_prefers_newer_worker_bundle(tmp_path: Path):
    repo = tmp_path / "repo"
    _seed_local_report(repo)
    _seed_worker_bundle(repo, "mba_m4_backtests_20260228T083052Z")

    head, worker_meta = snapshots._latest_backtest_head_with_worker_provenance(  # noqa: SLF001
        _local_leaderboard("2026-02-28T08:00:00Z"),
        repo,
    )

    assert head["source"] == "worker_inbox"
    assert head["bundle"] == "mba_m4_backtests_20260228T083052Z"
    assert head["timestamp_utc"] == "2026-02-28T08:30:52Z"
    assert head["reason"] == "worker bundle newer than local backtest"
    assert worker_meta["present"] is True
    assert worker_meta["ingested_into_state"] is True


def test_latest_backtest_head_falls_back_when_worker_summary_missing(tmp_path: Path):
    repo = tmp_path / "repo"
    _seed_local_report(repo)
    _seed_worker_bundle(repo, "mba_m4_backtests_20260228T083052Z", with_summary=False)

    head, worker_meta = snapshots._latest_backtest_head_with_worker_provenance(  # noqa: SLF001
        _local_leaderboard("2026-02-28T08:00:00Z"),
        repo,
    )

    assert head["source"] == "local"
    assert head["reason"] == "worker bundle incomplete; fallback to local"
    assert worker_meta["present"] is True
    assert "worker 產物不完整" in worker_meta["note"]


def test_timestamp_parse_edge_cases():
    assert snapshots._worker_bundle_ts_utc("mba_m4_backtests_20260228T083052Z") == "2026-02-28T08:30:52Z"  # noqa: SLF001
    assert snapshots._normalize_ts_utc("2026-02-28T08:30:52.146568") == "2026-02-28T08:30:52Z"  # noqa: SLF001
    assert snapshots._normalize_ts_utc("not-a-ts") is None  # noqa: SLF001
