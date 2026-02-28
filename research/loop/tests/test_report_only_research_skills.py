from __future__ import annotations

import json
from pathlib import Path

from research.loop.report_only_research_skills import (
    backtest_repro_gate,
    data_lineage_fingerprint,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def _seed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    git_dir = repo / ".git"
    (git_dir / "refs/heads").mkdir(parents=True)
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (git_dir / "refs/heads/main").write_text(
        "0123456789abcdef0123456789abcdef01234567\n",
        encoding="utf-8",
    )

    _write_json(
        repo / "reports/research/latest/summary.json",
        {
            "candidate_id": "vol_compression_v1__short__squeeze_release",
            "strategy_id": "vol_compression_v1",
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "timestamp": "2026-02-28T08:30:52Z",
            "start_ts": "2020-01-01T00:00:00Z",
            "end_ts": "2026-02-27T09:00:00Z",
            "sharpe": 0.57,
            "total_return": 0.10,
            "max_drawdown": -0.14,
            "trades_count": 85,
        },
    )
    _write_json(
        repo / "reports/research/latest/selection.json",
        {
            "generated_at": "2026-02-28T08:30:52Z",
            "regime": "BEAR",
            "regime_tf": "4h",
        },
    )
    _write_json(
        repo / "reports/state_atomic/regime_monitor_latest.json",
        {
            "ts_utc": "2026-02-28T08:55:33Z",
            "threshold_source_path": "research/policy/regime_thresholds.json",
            "threshold_policy_sha": "policy-sha-1",
            "threshold_policy_version": "regime_thresholds_v1",
            "last_calibrated_utc": "2026-02-27T13:18:04Z",
        },
    )
    _write_json(
        repo / "research/policy/regime_thresholds.json",
        {
            "name": "regime_thresholds_v1",
            "calibration": {"last_calibrated_utc": "2026-02-27T13:18:04Z"},
        },
    )
    _write_json(
        repo / "data/state/system_health_latest.json",
        {
            "generated_utc": "2026-02-28T08:55:33Z",
            "ssot_status": "OK",
        },
    )
    _write_json(
        repo / "data/state/freshness_table.json",
        {
            "generated_utc": "2026-02-28T08:55:33Z",
            "rows": [
                {
                    "symbol": "BTCUSDT",
                    "tf": "1h",
                    "source": "data/derived/BTCUSDT/1h/klines.jsonl",
                    "status": "OK",
                },
                {
                    "symbol": "ETHUSDT",
                    "tf": "4h",
                    "source": "data/derived/ETHUSDT/4h/klines.jsonl",
                    "status": "OK",
                },
            ],
        },
    )
    _write_json(
        repo / "data/state/daily_report_latest.json",
        {
            "generated_utc": "2026-02-28T08:55:33Z",
            "latest_backtest_head": {
                "artifacts": {
                    "summary": "reports/research/latest/summary.json",
                    "selection": "reports/research/latest/selection.json",
                }
            },
            "sources": {
                "system_health_latest": {
                    "path": "data/state/system_health_latest.json",
                    "exists": True,
                    "ts_utc": "2026-02-28T08:55:33Z",
                },
                "freshness_table": {
                    "path": "data/state/freshness_table.json",
                    "exists": True,
                    "ts_utc": "2026-02-28T08:55:33Z",
                },
                "research_leaderboard": {
                    "path": "data/state/_research/leaderboard.json",
                    "exists": True,
                    "ts_utc": "2026-02-28T08:27:28Z",
                },
            },
        },
    )

    (repo / "data/derived/BTCUSDT/1h").mkdir(parents=True)
    (repo / "data/derived/ETHUSDT/4h").mkdir(parents=True)
    (repo / "data/derived/BTCUSDT/1h/klines.jsonl").write_text("{}\n", encoding="utf-8")
    (repo / "data/derived/ETHUSDT/4h/klines.jsonl").write_text("{}\n", encoding="utf-8")
    return repo


def test_data_lineage_fingerprint_stable_hash_across_run_timestamps(tmp_path: Path):
    repo = _seed_repo(tmp_path)

    first = data_lineage_fingerprint(repo, now_utc="2026-02-28T10:00:00Z")
    second = data_lineage_fingerprint(repo, now_utc="2026-02-28T10:05:00Z")

    assert first["status"] == "OK"
    assert second["status"] == "OK"
    assert first["fingerprint_sha256"] == second["fingerprint_sha256"]
    assert first["fingerprint_material"]["regime_slice"] == "BEAR"
    assert first["fingerprint_material"]["symbols"] == ["BTCUSDT", "ETHUSDT"]
    assert "daily_report_latest" in first["daily_ssot_sources"]


def test_data_lineage_fingerprint_writes_artifacts(tmp_path: Path):
    repo = _seed_repo(tmp_path)

    out = data_lineage_fingerprint(
        repo,
        write_artifacts=True,
        output_dir="reports/runtime/lineage",
        now_utc="2026-02-28T10:00:00Z",
    )

    assert out["status"] == "OK"
    artifacts = out["artifacts"]
    assert Path(repo / artifacts["json"]).exists()
    assert Path(repo / artifacts["markdown"]).exists()


def test_backtest_repro_gate_ok_with_live_runner(tmp_path: Path):
    repo = _seed_repo(tmp_path)

    def runner(_: dict) -> dict:
        return {
            "sharpe": 0.57,
            "total_return": 0.10,
            "max_drawdown": -0.14,
            "trades_count": 85,
        }

    out = backtest_repro_gate(
        repo,
        candidate_id="vol_compression_v1__short__squeeze_release",
        slice_ref="BEAR@4h",
        code_ref="0123456789abcdef0123456789abcdef01234567",
        runs=3,
        runner=runner,
        now_utc="2026-02-28T10:00:00Z",
    )

    assert out["status"] == "OK"
    assert out["execution_mode"] == "live_runner"
    assert out["classification"]["status"] == "OK"
    assert out["diff_stats"]["sharpe"]["max_abs_diff"] == 0.0


def test_backtest_repro_gate_fail_on_drift(tmp_path: Path):
    repo = _seed_repo(tmp_path)

    def runner(payload: dict) -> dict:
        run_index = int(payload["run_index"])
        return {
            "sharpe": 0.57 + (0.08 * run_index),
            "total_return": 0.10,
            "max_drawdown": -0.14,
            "trades_count": 85,
        }

    out = backtest_repro_gate(repo, runs=3, runner=runner, now_utc="2026-02-28T10:00:00Z")

    assert out["status"] == "FAIL"
    assert out["classification"]["status"] == "FAIL"
    assert out["diff_stats"]["sharpe"]["max_abs_diff"] > out["thresholds"]["sharpe"]


def test_backtest_repro_gate_artifact_replay_warn_and_writes(tmp_path: Path):
    repo = _seed_repo(tmp_path)

    out = backtest_repro_gate(
        repo,
        runs=3,
        write_artifacts=True,
        output_dir="reports/runtime/repro_gate",
        now_utc="2026-02-28T10:00:00Z",
    )

    assert out["status"] == "WARN"
    assert out["execution_mode"] == "artifact_replay"
    assert len(out["runs"]) == 3
    assert out["classification"]["status"] == "WARN"
    artifacts = out["artifacts"]
    assert Path(repo / artifacts["json"]).exists()
    assert Path(repo / artifacts["markdown"]).exists()
