from typing import Dict, Any

def score_backtest_by_regime(metrics_per_regime: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, float]:
    """
    Calculate consolidated score for Bull/Bear regimes.
    Score = CAGR - alpha * MaxDD
    Input metrics_per_regime like {'BULL': {'cagr': 0.5, 'max_dd': -0.1}, ...}
    """
    config = config or {}
    alpha = config.get('alpha', 1.0)
    
    scores = {}
    
    for regime in ['BULL', 'BEAR', 'NEUTRAL']:
        m = metrics_per_regime.get(regime, {})
        if not m:
            scores[f'score_{regime.lower()}'] = -1.0 # Penalty for no data/metrics
            continue
            
        cagr = m.get('cagr', 0.0)
        max_dd = m.get('max_dd', 0.0)
        
        # MaxDD is usually negative (e.g. -0.2).
        # We want to penalize it. CAGR - alpha * abs(MaxDD) or CAGR + alpha * MaxDD (if MaxDD is neg)
        # Let's use: Score = CAGR - alpha * abs(MaxDD)
        
        score = cagr - alpha * abs(max_dd)
        scores[f'score_{regime.lower()}'] = score
        
    return scores
