import json
from pathlib import Path

from research.experiments.candidate_catalog import family_counts, phase2_pr1_candidates
from research.experiments.report_only_artifacts import (
    build_strategy_pool_payload,
    write_report_only_artifacts,
)
from research.loop import leaderboard


def test_phase2_pr1_candidate_coverage():
    candidates = phase2_pr1_candidates()
    counts = family_counts(candidates)

    assert 6 <= len(candidates) <= 10
    assert counts.get("trend", 0) >= 2
    assert counts.get("mean_reversion", 0) >= 2
    assert counts.get("volatility", 0) >= 2


def test_artifact_writer_and_leaderboard(monkeypatch, tmp_path):
    reports_root = tmp_path / "reports" / "research"
    run_dir = write_report_only_artifacts(reports_root, run_id="PR1_TEST")

    manifest_path = run_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["report_only"] is True
    assert len(manifest["entries"]) >= 6

    # Ensure each candidate produced the standard artifact trio + results payload.
    for row in manifest["entries"]:
        assert Path(row["summary_path"]).exists()
        assert Path(row["gate_path"]).exists()
        assert Path(row["selection_path"]).exists()
        assert Path(row["results_path"]).exists()

    monkeypatch.setattr(leaderboard, "REPORTS_ROOT", reports_root)
    entries = leaderboard.build_leaderboard(top_n=20)

    assert len(entries) >= 6
    sharpe_values = [e["oos_sharpe"] for e in entries]
    assert sharpe_values == sorted(sharpe_values, reverse=True)


def test_strategy_pool_payload_sorted(tmp_path):
    reports_root = tmp_path / "reports" / "research"
    run_dir = write_report_only_artifacts(reports_root, run_id="PR1_POOL")
    manifest = json.loads((run_dir / "manifest.json").read_text())

    payload = build_strategy_pool_payload(manifest)
    assert payload["report_only"] is True
    assert len(payload["candidates"]) >= 6

    last_scores = [row["last_score"] for row in payload["candidates"]]
    assert last_scores == sorted(last_scores, reverse=True)
