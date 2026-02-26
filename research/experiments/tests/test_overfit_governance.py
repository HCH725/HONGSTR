import json
from pathlib import Path

from research.experiments.overfit_governance import (
    build_quant_specialist_weekly_check,
    evaluate_weekly_governance,
    render_weekly_governance_markdown,
    write_weekly_governance_report,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _sample_entries():
    return [
        {
            "strategy_id": "trend_mvp_btc_1h",
            "direction": "LONG",
            "variant": "base",
            "is_sharpe": 1.3,
            "oos_sharpe": 1.1,
            "oos_mdd": -0.14,
            "oos_return": 0.22,
        },
        {
            "strategy_id": "trend_supertrend_eth_1h_short",
            "direction": "SHORT",
            "variant": "v_short",
            "is_sharpe": 1.0,
            "oos_sharpe": 0.83,
            "oos_mdd": -0.16,
            "oos_return": 0.14,
        },
        {
            "strategy_id": "vol_keltner_breakout_eth_1h",
            "direction": "LONG",
            "variant": "base",
            "is_sharpe": 0.9,
            "oos_sharpe": 0.8,
            "oos_mdd": -0.19,
            "oos_return": 0.08,
        },
        {
            "strategy_id": "mr_bbands_eth_1h",
            "direction": "LONG",
            "variant": "base",
            "is_sharpe": 1.7,
            "oos_sharpe": 0.6,
            "oos_mdd": -0.3,
            "oos_return": 0.05,
        },
    ]


def test_weekly_governance_recommendations_schema():
    payload = evaluate_weekly_governance(
        _sample_entries(),
        week_id="2026-W09",
        generated_at="2026-02-27T00:00:00+00:00",
    )
    assert payload["schema_version"] == "governance_weekly_v1"
    assert payload["report_only"] is True
    assert payload["actions"] == []
    assert payload["summary"] == {"total": 4, "promote": 2, "demote": 1, "watchlist": 1}

    recs = payload["recommendations"]
    by_id = {row["strategy_id"]: row for row in recs}
    assert by_id["trend_mvp_btc_1h"]["recommendation"] == "promote"
    assert by_id["trend_supertrend_eth_1h_short"]["recommendation"] == "promote"
    assert by_id["vol_keltner_breakout_eth_1h"]["recommendation"] == "watchlist"
    assert by_id["mr_bbands_eth_1h"]["recommendation"] == "demote"
    assert by_id["mr_bbands_eth_1h"]["hard_gates"]["pass"] is False


def test_weekly_governance_markdown_matches_golden():
    payload = evaluate_weekly_governance(
        _sample_entries(),
        week_id="2026-W09",
        generated_at="2026-02-27T00:00:00+00:00",
    )
    md = render_weekly_governance_markdown(payload)
    golden = (FIXTURES / "weekly_governance_golden.md").read_text(encoding="utf-8")
    assert md.strip() == golden.strip()


def test_write_weekly_report_and_quant_specialist_payload(tmp_path):
    payload = build_quant_specialist_weekly_check(
        _sample_entries(),
        week_id="2026-W09",
        generated_at="2026-02-27T00:00:00+00:00",
    )
    assert payload["skill"] == "overfit_governance_weekly_check"
    assert payload["constraints"] == ["read_only", "report_only"]
    assert payload["report_only"] is True
    assert payload["actions"] == []

    out_path = write_weekly_governance_report(payload, tmp_path / "reports" / "governance")
    assert out_path.exists()
    assert out_path.name == "governance_2026-W09.md"
    assert "report_only" in out_path.read_text(encoding="utf-8")
