import json
import os

from hongstr.selection.selector import Selector


def test_selection_artifact_roundtrip(tmp_path):
    policy = {
        'enabled_regimes': ['BULL', 'BEAR'],
        'top_k_bull': 3,
        'top_k_bear': 3,
        'neutral_policy': 'NO_TRADE'
    }
    selector = Selector(policy)

    selection = {
        'BULL': ['A', 'B'],
        'BEAR': ['C'],
        'NEUTRAL': []
    }

    outfile = tmp_path / "test_selected.json"

    selector.save_selection("TEST_PF", selection, str(outfile))

    assert os.path.exists(outfile)

    loaded = selector.load_selection(str(outfile))
    assert loaded['schema_version'] == "selection_artifact_v1"
    assert loaded['portfolio_id'] == "TEST_PF"
    assert "timestamp_gmt8" in loaded
    assert loaded['selection']['BULL'] == ['A', 'B']
    assert "git_commit" in loaded['metadata']
    assert isinstance(loaded['metadata']['git_commit'], str)

def test_selection_neutral_guard(tmp_path):
    # Policy says NO_TRADE
    policy = {
        'enabled_regimes': ['BULL'],
        'neutral_policy': 'NO_TRADE'
    }
    selector = Selector(policy)

    # Try to save a non-empty neutral
    selection = {
        'BULL': [],
        'BEAR': [],
        'NEUTRAL': ['DANGEROUS']
    }

    outfile = tmp_path / "guard.json"
    selector.save_selection("TEST_PF", selection, str(outfile))

    # Check file content directly
    with open(outfile) as f:
        data = json.load(f)
        # Should be empty
        assert data['selection']['NEUTRAL'] == []

    # Check load_selection
    loaded = selector.load_selection(str(outfile))
    assert loaded['selection']['NEUTRAL'] == []
