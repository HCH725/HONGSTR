from typing import Callable, Dict, List, Any
from dataclasses import dataclass

@dataclass
class FactorDef:
    name: str              # Unique factor name, e.g., "ema_diff_10_20"
    required_cols: List[str] # Columns needed from the Panel, e.g., ["close"]
    window: int              # Lookback window needed to compute (e.g. 20)
    shift: int               # Lag needed so we don't have look-ahead bias (usually 1)
    func: Callable           # The pure function to compute it

class FactorRegistry:
    _factors: Dict[str, FactorDef] = {}
    _sets: Dict[str, List[str]] = {}

    @classmethod
    def register_factor(cls, factor: FactorDef):
        if factor.name in cls._factors:
            import logging
            logging.warning(f"Factor {factor.name} is already registered. Overwriting.")
        cls._factors[factor.name] = factor

    @classmethod
    def register_set(cls, set_name: str, factor_names: List[str]):
        cls._sets[set_name] = factor_names

    @classmethod
    def get_factor(cls, name: str) -> FactorDef:
        if name not in cls._factors:
            raise KeyError(f"Factor '{name}' not found in registry.")
        return cls._factors[name]

    @classmethod
    def get_set(cls, set_name: str) -> List[FactorDef]:
        if set_name not in cls._sets:
            raise KeyError(f"Factor set '{set_name}' not found in registry.")
        return [cls.get_factor(f) for f in cls._sets[set_name]]
