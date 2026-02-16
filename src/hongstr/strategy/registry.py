from typing import Dict, List, Type
from hongstr.strategy.core import StrategyTemplate
from hongstr.strategy.templates.initial import VWAPSupertrend, RSIMACD, BBRSI
from hongstr.portfolio.core import PortfolioType

class StrategyRegistry:
    def __init__(self):
        self._templates: Dict[str, Type[StrategyTemplate]] = {}
        # Register defaults
        self.register("vwap_supertrend", VWAPSupertrend)
        self.register("rsi_macd", RSIMACD)
        self.register("bb_rsi", BBRSI)

    def register(self, name: str, cls: Type[StrategyTemplate]):
        self._templates[name] = cls

    def get_template_class(self, name: str) -> Type[StrategyTemplate]:
        return self._templates.get(name)

    def get_templates(self, pool: str) -> List[str]:
        """Return list of template names eligible for the pool."""
        eligible = []
        for name, cls in self._templates.items():
            inst = cls("temp")
            req_tf = set(inst.required_timeframes)
            
            if pool == "HONG":
                # HONG allowed: subset of {1h, 4h}
                allowed = {"1h", "4h"}
                if req_tf.issubset(allowed):
                    eligible.append(name)
            else:
                # LAB allows all
                eligible.append(name)
        return eligible

    def validate_strategy_config(self, strategy_name: str, pool: str) -> bool:
        cls = self.get_template_class(strategy_name)
        if not cls:
            return False
            
        if pool == "HONG":
            inst = cls("temp")
            req_tf = set(inst.required_timeframes)
            allowed = {"1h", "4h"}
            if not req_tf.issubset(allowed):
                return False
        
        return True
