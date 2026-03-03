"""
Phase-2 research candidates (report_only).

This catalog is intentionally isolated to research/** so we can expand strategy
coverage without changing src/hongstr/** execution semantics.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    family: str
    strategy: str
    symbol: str
    timeframe: str
    parameters: Dict[str, float]
    direction: str = "long"
    variant: str = "base"


def phase2_pr1_candidates() -> List[StrategyCandidate]:
    """
    Candidate set for PR-1:
    - 6~10 strategies total
    - trend / mean_reversion / volatility each >= 2
    """
    return [
        StrategyCandidate(
            strategy_id="trend_mvp_btc_1h",
            family="trend",
            strategy="trend_mvp",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={"fast_ema": 12, "slow_ema": 26},
        ),
        StrategyCandidate(
            strategy_id="trend_supertrend_eth_1h",
            family="trend",
            strategy="supertrend",
            symbol="ETHUSDT",
            timeframe="1h",
            parameters={"atr_period": 10, "atr_mult": 2.5},
        ),
        StrategyCandidate(
            strategy_id="trend_ma_cross_bnb_4h",
            family="trend",
            strategy="ma_cross",
            symbol="BNBUSDT",
            timeframe="4h",
            parameters={"fast_ma": 20, "slow_ma": 80},
        ),
        StrategyCandidate(
            strategy_id="mr_rsi2_btc_1h",
            family="mean_reversion",
            strategy="rsi2_reversion",
            symbol="BTCUSDT",
            timeframe="1h",
            parameters={"rsi_period": 2, "entry": 20, "exit": 55},
        ),
        StrategyCandidate(
            strategy_id="mr_bbands_eth_1h",
            family="mean_reversion",
            strategy="bbands_reversion",
            symbol="ETHUSDT",
            timeframe="1h",
            parameters={"window": 20, "std_mult": 2.0},
        ),
        StrategyCandidate(
            strategy_id="mr_zscore_bnb_1h",
            family="mean_reversion",
            strategy="zscore_reversion",
            symbol="BNBUSDT",
            timeframe="1h",
            parameters={"lookback": 48, "z_entry": 1.8},
        ),
        StrategyCandidate(
            strategy_id="vol_atr_breakout_btc_4h",
            family="volatility",
            strategy="atr_breakout",
            symbol="BTCUSDT",
            timeframe="4h",
            parameters={"atr_period": 14, "break_mult": 1.2},
        ),
        StrategyCandidate(
            strategy_id="vol_keltner_breakout_eth_1h",
            family="volatility",
            strategy="keltner_breakout",
            symbol="ETHUSDT",
            timeframe="1h",
            parameters={"ema_window": 20, "atr_mult": 1.5},
        ),
    ]


def family_counts(candidates: Iterable[StrategyCandidate]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for candidate in candidates:
        counts[candidate.family] = counts.get(candidate.family, 0) + 1
    return counts


def phase2_pr2_candidates() -> List[StrategyCandidate]:
    """
    PR-2 extends PR-1 with direction variants for two strategies:
    - supertrend
    - ma_cross

    Required proof point: leaderboard includes long + short/longshort entries.
    """
    base = phase2_pr1_candidates()
    variants = [
        StrategyCandidate(
            strategy_id="trend_supertrend_eth_1h_short",
            family="trend",
            strategy="supertrend",
            symbol="ETHUSDT",
            timeframe="1h",
            parameters={"atr_period": 10, "atr_mult": 2.5},
            direction="short",
            variant="v_short",
        ),
        StrategyCandidate(
            strategy_id="trend_supertrend_eth_1h_longshort",
            family="trend",
            strategy="supertrend",
            symbol="ETHUSDT",
            timeframe="1h",
            parameters={"atr_period": 10, "atr_mult": 2.5},
            direction="longshort",
            variant="v_longshort",
        ),
        StrategyCandidate(
            strategy_id="trend_ma_cross_bnb_4h_short",
            family="trend",
            strategy="ma_cross",
            symbol="BNBUSDT",
            timeframe="4h",
            parameters={"fast_ma": 20, "slow_ma": 80},
            direction="short",
            variant="v_short",
        ),
        StrategyCandidate(
            strategy_id="trend_ma_cross_bnb_4h_longshort",
            family="trend",
            strategy="ma_cross",
            symbol="BNBUSDT",
            timeframe="4h",
            parameters={"fast_ma": 20, "slow_ma": 80},
            direction="longshort",
            variant="v_longshort",
        ),
    ]
    return [*base, *variants]
