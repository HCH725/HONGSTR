from research.factors.registry import FactorDef, FactorRegistry
from research.factors.ops import returns_1, ema_diff, atr_n, vola_n, breakout_n

# Register individual factors

FactorRegistry.register_factor(FactorDef(
    name="ret_1",
    required_cols=["close"],
    window=2,
    shift=1,
    func=lambda df: returns_1(df["close"], shift=1)
))

FactorRegistry.register_factor(FactorDef(
    name="ema_diff_10_20",
    required_cols=["close"],
    window=20,
    shift=1,
    func=lambda df: ema_diff(df["close"], fast=10, slow=20, shift=1)
))

FactorRegistry.register_factor(FactorDef(
    name="atr_14",
    required_cols=["high", "low", "close"],
    window=15,
    shift=1,
    func=lambda df: atr_n(df["high"], df["low"], df["close"], n=14, shift=1)
))

FactorRegistry.register_factor(FactorDef(
    name="vola_20",
    required_cols=["close"],
    window=20,
    shift=1,
    func=lambda df: vola_n(df["close"], n=20, shift=1)
))

FactorRegistry.register_factor(FactorDef(
    name="breakout_14_high",
    required_cols=["high"],
    window=14,
    shift=1,
    func=lambda df: breakout_n(df["high"], n=14, type="high", shift=1)
))

FactorRegistry.register_factor(FactorDef(
    name="breakout_14_low",
    required_cols=["low"],
    window=14,
    shift=1,
    func=lambda df: breakout_n(df["low"], n=14, type="low", shift=1)
))

# Register the MVP set
FactorRegistry.register_set(
    set_name="trend_mvp",
    factor_names=["ret_1", "ema_diff_10_20", "atr_14", "vola_20", "breakout_14_high", "breakout_14_low"]
)
