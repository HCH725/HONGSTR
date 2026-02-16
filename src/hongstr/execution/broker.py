from abc import ABC, abstractmethod
from typing import List, Optional
from hongstr.execution.models import OrderRequest, OrderResult, Position

class AbstractBroker(ABC):
    @abstractmethod
    def place_order(self, order: OrderRequest) -> OrderResult:
        pass

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> bool:
        pass

    @abstractmethod
    def get_open_orders(self, symbol: str) -> List[dict]:
        pass

    @abstractmethod
    def get_position(self, symbol: str) -> Position:
        """Should return net position for symbol (or hedge side if specified in symbol/context)"""
        pass
    
    @abstractmethod
    def get_account_balance(self) -> float:
        pass

    @abstractmethod
    def ping(self) -> bool:
        pass
