from collections import defaultdict

from research.loop.candidate_catalog import build_candidate_catalog


def test_catalog_has_multi_family_and_multiple_strategies():
    catalog = build_candidate_catalog(include_dca=True)
    assert len(catalog) >= 12

    strategies_by_family = defaultdict(set)
    for c in catalog:
        strategies_by_family[c["family"]].add(c["strategy_id"])

    assert len(strategies_by_family["trend"]) >= 2
    assert len(strategies_by_family["mr"]) >= 2
    assert len(strategies_by_family["vol"]) >= 2


def test_catalog_has_direction_variants_for_two_strategies():
    catalog = build_candidate_catalog(include_dca=True)
    dirs_by_strategy = defaultdict(set)
    for c in catalog:
        dirs_by_strategy[c["strategy_id"]].add(c["direction"])

    assert dirs_by_strategy["supertrend_v2"] >= {"LONG", "SHORT", "LONGSHORT"}
    assert dirs_by_strategy["ema_cross_v3"] >= {"LONG", "SHORT", "LONGSHORT"}


def test_dca_sweep_generates_param_variants():
    catalog = [c for c in build_candidate_catalog(include_dca=True) if c["family"] == "dca1"]
    assert catalog

    ids = {c["candidate_id"] for c in catalog}
    assert len(ids) == len(catalog)

    trailing_set = {float(c["parameters"].get("trailing_pct", -1)) for c in catalog}
    spacing_set = {float(c["parameters"].get("spacing_pct", -1)) for c in catalog}
    assert len(trailing_set) >= 2
    assert len(spacing_set) >= 2
