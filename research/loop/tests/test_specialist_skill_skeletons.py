from pathlib import Path

from research.loop.specialist_skill_skeletons import (
    backtest_reproducibility_audit,
    factor_health_and_drift_report,
    strategy_regime_sensitivity_report,
)

REPO = Path("/Users/hong/Projects/HONGSTR")
FIX = REPO / "research/loop/tests/fixtures/specialist_skills"


def test_backtest_reproducibility_unknown_when_missing():
    out = backtest_reproducibility_audit(REPO, manifest_path="reports/research/missing_manifest.json")
    assert out["status"] in {"UNKNOWN", "WARN"}
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["missing_artifacts"]
    assert "refresh_state.sh" in out["refresh_hint"]


def test_factor_health_unknown_when_missing():
    out = factor_health_and_drift_report(REPO, factor_manifest_path="reports/research/missing_factor_manifest.json")
    assert out["status"] in {"UNKNOWN", "WARN"}
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["missing_artifacts"]
    assert "refresh_state.sh" in out["refresh_hint"]


def test_regime_sensitivity_unknown_when_missing():
    out = strategy_regime_sensitivity_report(REPO, regime_report_path="reports/research/missing_regime_report.json")
    assert out["status"] in {"UNKNOWN", "WARN"}
    assert out["report_only"] is True
    assert out["actions"] == []
    assert out["missing_artifacts"]
    assert "refresh_state.sh" in out["refresh_hint"]


def test_backtest_reproducibility_ok_with_fixture():
    rel = str(FIX.relative_to(REPO) / "backtest_manifest.json")
    out = backtest_reproducibility_audit(REPO, manifest_path=rel)
    assert out["status"] == "OK"
    assert any("git_commit=" in x for x in out["findings"])


def test_factor_health_ok_with_fixture():
    rel = str(FIX.relative_to(REPO) / "factor_manifest.json")
    out = factor_health_and_drift_report(REPO, factor_manifest_path=rel)
    assert out["status"] == "OK"
    assert any("drift_score=" in x for x in out["findings"])


def test_regime_sensitivity_ok_with_fixture():
    rel = str(FIX.relative_to(REPO) / "regime_sensitivity.json")
    out = strategy_regime_sensitivity_report(REPO, regime_report_path=rel)
    assert out["status"] == "OK"
    assert any("sensitivity=" in x for x in out["findings"])


def test_backtest_missing_manifest_but_ssot_evidence_warn(tmp_path):
    repo = tmp_path / "repo"
    (repo / "data/state").mkdir(parents=True)
    (repo / "reports/state_atomic").mkdir(parents=True)
    (repo / "data/state/system_health_latest.json").write_text('{"ssot_status":"WARN"}', encoding="utf-8")
    (repo / "reports/state_atomic/coverage_table.jsonl").write_text('{"status":"DONE"}\n', encoding="utf-8")

    out = backtest_reproducibility_audit(repo, manifest_path="reports/research/missing_manifest.json")
    assert out["status"] == "WARN"
    assert out["missing_artifacts"]
    assert out["evidence_refs"]
    assert any("coverage_table.jsonl" in x for x in out["evidence_refs"])
    assert any("system_health_latest.json" in x for x in out["evidence_refs"])


def test_regime_missing_artifact_but_state_atomic_warn(tmp_path):
    repo = tmp_path / "repo"
    (repo / "reports/state_atomic").mkdir(parents=True)
    (repo / "reports/state_atomic/regime_monitor_latest.json").write_text(
        '{"status":"WARN"}',
        encoding="utf-8",
    )

    out = strategy_regime_sensitivity_report(repo, regime_report_path="reports/research/missing_regime.json")
    assert out["status"] == "WARN"
    assert out["missing_artifacts"]
    assert out["evidence_refs"]
    assert any("reports/state_atomic/regime_monitor_latest.json" in x for x in out["evidence_refs"])
