import json
from pathlib import Path

from research.loop import leaderboard as lb


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_metrics_present_are_propagated(monkeypatch, tmp_path: Path):
    reports_root = tmp_path / "reports" / "research"
    run_dir = reports_root / "20260227" / "cand_nonzero"
    _write_json(
        run_dir / "summary.json",
        {
            "candidate_id": "cand_nonzero",
            "strategy_id": "trend_mvp_btc_1h",
            "family": "trend",
            "direction": "LONG",
            "variant": "base",
            "status": "SUCCESS",
            "sharpe": 1.37,
            "max_drawdown": -0.11,
            "is_sharpe": 1.92,
            "trades_count": 42,
            "timestamp": "2026-02-27T00:00:00Z",
        },
    )
    _write_json(
        run_dir / "gate.json",
        {
            "overall": "PASS",
            "final_score": 108.4,
        },
    )

    out_path = tmp_path / "data" / "state" / "_research" / "leaderboard.json"
    monkeypatch.setattr(lb, "REPORTS_ROOT", reports_root)
    monkeypatch.setattr(lb, "LEADERBOARD_PATH", out_path)

    lb.save_leaderboard(top_n=5)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    entry = payload["entries"][0]

    assert entry["candidate_id"] == "cand_nonzero"
    assert entry["final_score"] == 108.4
    assert entry["oos_sharpe"] == 1.37
    assert entry["oos_mdd"] == -0.11
    assert entry["metrics_status"] == "OK"
    assert entry["metrics_unavailable_reason"] is None


def test_dry_run_metrics_are_unknown_not_zero(monkeypatch, tmp_path: Path):
    reports_root = tmp_path / "reports" / "research"
    run_dir = reports_root / "20260227" / "cand_dry"
    _write_json(
        run_dir / "summary.json",
        {
            "candidate_id": "cand_dry",
            "strategy_id": "supertrend_v2",
            "family": "trend",
            "direction": "SHORT",
            "variant": "base",
            "status": "DRY_RUN",
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "trades_count": 0,
            "timestamp": "2026-02-27T00:00:00Z",
        },
    )
    _write_json(
        run_dir / "gate.json",
        {
            "overall": "FAIL",
            "final_score": 0.0,
        },
    )

    out_path = tmp_path / "data" / "state" / "_research" / "leaderboard.json"
    monkeypatch.setattr(lb, "REPORTS_ROOT", reports_root)
    monkeypatch.setattr(lb, "LEADERBOARD_PATH", out_path)

    lb.save_leaderboard(top_n=5)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    entry = payload["entries"][0]

    assert entry["status"] == "DRY_RUN"
    assert entry["metrics_status"] == "UNKNOWN"
    assert entry["metrics_unavailable_reason"] == "dry_run_artifact"
    assert entry["oos_sharpe"] is None
    assert entry["oos_mdd"] is None
    assert entry["final_score"] is None


def test_missing_metrics_mark_unknown_with_reason(monkeypatch, tmp_path: Path):
    reports_root = tmp_path / "reports" / "research"
    run_dir = reports_root / "20260227" / "cand_missing"
    _write_json(
        run_dir / "summary.json",
        {
            "candidate_id": "cand_missing",
            "strategy_id": "ema_cross_v3",
            "family": "trend",
            "direction": "LONG",
            "variant": "base",
            "status": "SUCCESS",
            "timestamp": "2026-02-27T00:00:00Z",
        },
    )
    _write_json(
        run_dir / "gate.json",
        {
            "overall": "UNKNOWN",
            "final_score": None,
        },
    )

    out_path = tmp_path / "data" / "state" / "_research" / "leaderboard.json"
    monkeypatch.setattr(lb, "REPORTS_ROOT", reports_root)
    monkeypatch.setattr(lb, "LEADERBOARD_PATH", out_path)

    lb.save_leaderboard(top_n=5)
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    entry = payload["entries"][0]

    assert entry["metrics_status"] == "UNKNOWN"
    assert str(entry["metrics_unavailable_reason"]).startswith("missing_metrics:")
    assert entry["oos_sharpe"] is None
    assert entry["final_score"] is None
    assert entry["oos_sharpe"] != 0.0
