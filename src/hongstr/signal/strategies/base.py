from abc import ABC, abstractmethod
from typing import List, Optional
from ..types import Bar, SignalEvent

class BaseStrategy(ABC):
    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id

    @property
    @abstractmethod
    def required_timeframes(self) -> List[str]:
        pass

    @abstractmethod
    def on_bars(self, symbol: str, timeframe: str, bars: List[Bar]) -> Optional[SignalEvent]:
        """
        Called when a new closed bar is available for the given symbol and timeframe.
        'bars' contains the history up to the latest closed bar.
        Returns a SignalEvent or None.
        """
        pass
