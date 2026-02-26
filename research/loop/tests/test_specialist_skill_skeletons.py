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
    assert out["status"] == "UNKNOWN"
    assert out["report_only"] is True
    assert out["missing_artifacts"]


def test_factor_health_unknown_when_missing():
    out = factor_health_and_drift_report(REPO, factor_manifest_path="reports/research/missing_factor_manifest.json")
    assert out["status"] == "UNKNOWN"
    assert out["report_only"] is True
    assert out["missing_artifacts"]


def test_regime_sensitivity_unknown_when_missing():
    out = strategy_regime_sensitivity_report(REPO, regime_report_path="reports/research/missing_regime_report.json")
    assert out["status"] == "UNKNOWN"
    assert out["report_only"] is True
    assert out["missing_artifacts"]


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
