import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

from hongstr.selection.selector import Selector


def demo_selection():
    print("--- Selection Demo ---")

    # Mock Backtest Results for 3 strategies
    # Spec: candidates need 'strategy_id' and 'scores'

    # Strat A: Great Bull, Bad Bear
    cand_a = {
        "strategy_id": "Strat_A_Trend",
        "scores": {"score_bull": 2.5, "score_bear": -0.5, "score_neutral": 0.0},
    }

    # Strat B: Good Bear, Bad Bull
    cand_b = {
        "strategy_id": "Strat_B_Hedge",
        "scores": {"score_bull": -0.2, "score_bear": 1.5, "score_neutral": 0.1},
    }

    # Strat C: Ok Both
    cand_c = {
        "strategy_id": "Strat_C_Balanced",
        "scores": {"score_bull": 1.0, "score_bear": 0.8, "score_neutral": 0.5},
    }

    candidates = [cand_a, cand_b, cand_c]

    # Policy
    policy = {
        "enabled_regimes": ["BULL", "BEAR"],
        "top_k_bull": 3,
        "top_k_bear": 3,
        "neutral_policy": "NO_TRADE",
    }

    selector = Selector(policy)
    selected = selector.select(candidates)

    print("\nPolicy:", policy)
    print("\nSelected Sets:")
    print(f"BULL: {selected['BULL']}")
    print(f"BEAR: {selected['BEAR']}")
    print(f"NEUTRAL: {selected['NEUTRAL']}")

    # Save
    out_path = Selector.DEFAULT_SELECTION_PATH

    # Inject a non-empty neutral to test normalization (Phase 0 policy is NO_TRADE)
    # The selector logic already produces empty if not enabled, but let's manually tamper
    # to prove save_selection fixes it.
    selected["NEUTRAL"] = ["Should_Be_Gone"]

    selector.save_selection(
        portfolio_id="HONG",
        selection=selected,
        path=out_path,
        extra_meta={
            "data_version": "c4_demo",
            "backtest_semantics_version": "1.0.0",
            "regime_version": "baseline_v1",
        },
    )
    print(f"\nSaved to {out_path}")

    # Verify load
    loaded = selector.load_selection(out_path)
    print("Loaded Neutral Set (should be empty):", loaded["selection"]["NEUTRAL"])


if __name__ == "__main__":
    demo_selection()
