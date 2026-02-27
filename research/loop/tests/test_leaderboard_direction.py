import json
from pathlib import Path

from research.loop import leaderboard as lb


def test_entry_from_summary_keeps_direction_and_variant(tmp_path: Path):
    run_dir = tmp_path / "runA"
    run_dir.mkdir(parents=True)

    summary = {
        "candidate_id": "cand_short_01",
        "strategy_id": "supertrend_v2",
        "family": "trend",
        "direction": "SHORT",
        "variant": "atr_follow",
        "sharpe": 0.88,
        "max_drawdown": -0.12,
        "trades_count": 18,
        "timestamp": "2026-02-27T00:00:00+00:00",
        "status": "SUCCESS",
    }
    gate = {"overall": "PASS", "final_score": 104.3}
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "gate.json").write_text(json.dumps(gate), encoding="utf-8")

    entry = lb._entry_from_summary(run_dir / "summary.json")
    assert entry is not None
    assert entry["direction"] == "SHORT"
    assert entry["variant"] == "atr_follow"
    assert entry["final_score"] == 104.3


def test_entry_from_summary_regime_backward_compat(tmp_path: Path):
    run_dir = tmp_path / "runB"
    run_dir.mkdir(parents=True)

    summary = {
        "candidate_id": "cand_legacy_01",
        "strategy_id": "ema_cross_v3",
        "family": "trend",
        "direction": "LONG",
        "variant": "base",
        "sharpe": 0.65,
        "max_drawdown": -0.17,
        "trades_count": 11,
        "timestamp": "2026-02-27T00:00:00+00:00",
        "status": "SUCCESS",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run_dir / "gate.json").write_text(json.dumps({"overall": "WARN"}), encoding="utf-8")

    entry = lb._entry_from_summary(run_dir / "summary.json")
    assert entry is not None
    assert entry["regime_slice"] == "ALL"
    assert entry["regime_window_utc"] is None
    assert entry["slice_rationale"] == "default_all_no_slice"
    assert entry["fallback_reason"] is None
    assert entry["metrics_status"] == "OK"


def test_build_leaderboard_keeps_same_candidate_across_slices(tmp_path: Path, monkeypatch):
    reports_root = tmp_path / "reports" / "research" / "20260227"
    run_all = reports_root / "cand_mix"
    run_bull = reports_root / "cand_mix__slice_bull"
    run_all.mkdir(parents=True, exist_ok=True)
    run_bull.mkdir(parents=True, exist_ok=True)

    (run_all / "summary.json").write_text(
        json.dumps(
            {
                "candidate_id": "cand_mix",
                "strategy_id": "supertrend_v2",
                "direction": "LONG",
                "variant": "base",
                "regime_slice": "ALL",
                "sharpe": 0.8,
                "max_drawdown": -0.11,
                "timestamp": "2026-02-27T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (run_all / "gate.json").write_text(json.dumps({"overall": "PASS", "final_score": 70.0}), encoding="utf-8")

    (run_bull / "summary.json").write_text(
        json.dumps(
            {
                "candidate_id": "cand_mix",
                "strategy_id": "supertrend_v2",
                "direction": "LONG",
                "variant": "base",
                "regime_slice": "BULL",
                "regime_window_start_utc": "2026-01-01T00:00:00Z",
                "regime_window_end_utc": "2026-04-01T00:00:00Z",
                "slice_rationale": "slice_applied",
                "sharpe": 1.1,
                "max_drawdown": -0.09,
                "timestamp": "2026-02-27T01:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (run_bull / "gate.json").write_text(json.dumps({"overall": "PASS", "final_score": 83.0}), encoding="utf-8")

    monkeypatch.setattr(lb, "REPORTS_ROOT", reports_root)
    out = lb.build_leaderboard(top_n=10)
    assert len(out) == 2
    slices = {row["regime_slice"] for row in out}
    assert slices == {"ALL", "BULL"}
    keys = {row["slice_comparison_key"] for row in out}
    assert len(keys) == 2
