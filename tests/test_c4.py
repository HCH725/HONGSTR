import pytest
import pandas as pd
import numpy as np
import os
import json
from hongstr.strategy.registry import StrategyRegistry
from hongstr.regime.baseline import RegimeLabeler
from hongstr.selection.scoring import score_backtest_by_regime
from hongstr.selection.selector import Selector

def test_registry_filters():
    reg = StrategyRegistry()
    
    # HONG pool should allow VWAP (1h) and RSI_MACD (4h) but not BB_RSI (15m)
    hong_templates = reg.get_templates("HONG")
    assert "vwap_supertrend" in hong_templates
    assert "rsi_macd" in hong_templates
    assert "bb_rsi" not in hong_templates
    
    # LAB pool allows all
    lab_templates = reg.get_templates("LAB")
    assert "bb_rsi" in lab_templates
    
    # Validation logic
    assert reg.validate_strategy_config("vwap_supertrend", "HONG") is True
    assert reg.validate_strategy_config("bb_rsi", "HONG") is False

def test_regime_labeling():
    # Synthetic data
    # Create trending up
    idx = pd.date_range("2024-01-01", periods=300, freq="4h")
    # Close increasing steadily
    close = np.linspace(100, 200, 300)
    df = pd.DataFrame({'close': close}, index=idx)
    
    # EMAs will lag close. Close > EMA200 * (1+z) should eventually happen.
    
    labeler = RegimeLabeler(hysteresis=0.0)
    labels = labeler.label_regime(df)
    
    assert labels.value_counts()['BULL'] > 0
    # Should not have BEAR
    assert 'BEAR' not in labels.value_counts()

def test_scoring_selector(tmp_path):
    # Mock scores
    cand1 = {
        'strategy_id': 'strat_good',
        'scores': {'score_bull': 0.5, 'score_bear': 0.1}
    }
    cand2 = {
        'strategy_id': 'strat_ok',
        'scores': {'score_bull': 0.3, 'score_bear': 0.2}
    }
    cand3 = {
        'strategy_id': 'strat_bad',
        'scores': {'score_bull': -99, 'score_bear': -99} # Invalid/No data
    }
    
    policy = {
        'enabled_regimes': ['BULL', 'BEAR'],
        'top_k_bull': 2,
        'top_k_bear': 1,
        'neutral_policy': 'NO_TRADE'
    }
    
    selector = Selector(policy)
    selected = selector.select([cand1, cand2, cand3])
    
    assert selected['BULL'] == ['strat_good', 'strat_ok'] # Top 2
    assert selected['BEAR'] == ['strat_ok'] # Top 1 (strat_ok has 0.2 vs strat_good 0.1)
    
    # JSON Persistence
    outfile = tmp_path / "sel.json"
    selector.save_selection("hong_test", selected, str(outfile), extra_meta={"v": 1})
    
    with open(outfile) as f:
        data = json.load(f)
        assert data['portfolio_id'] == "hong_test"
        assert data['selection']['BULL'] == ['strat_good', 'strat_ok']
