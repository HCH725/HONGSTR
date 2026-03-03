import json

from research.experiments.dca1_executor import (
    DCA1Config,
    simulate_dca1_path,
    write_dca1_research_run,
)
from research.experiments.report_only_artifacts import build_strategy_pool_payload
from research.loop import leaderboard


def test_simulate_dca1_fills_safety_and_hits_tp():
    prices = [100.0, 99.1, 97.8, 99.5, 102.2, 103.0]
    out = simulate_dca1_path(prices, DCA1Config())

    assert out["safety_filled"] is True
    assert out["exit_reason"] == "TAKE_PROFIT"
    assert out["total_return"] > 0


def test_simulate_dca1_optional_trailing_stop():
    prices = [100.0, 98.0, 101.0, 104.0, 106.0, 104.5]
    cfg = DCA1Config(trailing_pct=0.01)
    out = simulate_dca1_path(prices, cfg)

    assert out["safety_filled"] is True
    assert out["exit_reason"] == "TRAILING_STOP"


def test_write_dca1_run_is_leaderboard_and_pool_compatible(monkeypatch, tmp_path):
    reports_root = tmp_path / "reports" / "research"
    run_root = write_dca1_research_run(reports_root, run_id="PR3_DCA")
    manifest = json.loads((run_root / "manifest.json").read_text())

    assert manifest["report_only"] is True
    entry = manifest["entries"][0]
    assert entry["variant"] == "dca1_research"

    payload = build_strategy_pool_payload(manifest)
    assert payload["report_only"] is True
    assert len(payload["candidates"]) == 1

    monkeypatch.setattr(leaderboard, "REPORTS_ROOT", reports_root)
    entries = leaderboard.build_leaderboard(top_n=10)
    assert any(row["experiment_id"] == entry["strategy_id"] for row in entries)
