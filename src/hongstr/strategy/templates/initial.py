from hongstr.strategy.core import StrategyTemplate
from typing import List, Dict, Any
import pandas as pd
import numpy as np

class VWAPSupertrend(StrategyTemplate):
    @property
    def required_timeframes(self) -> List[str]:
        return ["1h"] # Example HONG eligible

    def compute_features(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        df = data["1h"].copy()
        # Dummy VWAP (Close) and Supertrend (Trend) for template
        df['vwap'] = df['close'] # Placeholder
        df['supertrend'] = 1 # 1=Bull, -1=Bear
        return df

    def signal(self, row: pd.Series, params: Dict[str, Any]) -> str:
        # Dummy logic
        if row['close'] > row['vwap'] and row['supertrend'] == 1:
            return 'LONG'
        if row['close'] < row['vwap'] and row['supertrend'] == -1:
            return 'SHORT'
        return 'FLAT'

class RSIMACD(StrategyTemplate):
    @property
    def required_timeframes(self) -> List[str]:
        return ["4h"] # Example HONG eligible

    def compute_features(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        df = data["4h"].copy()
        # Dummy RSI/MACD
        df['rsi'] = 50
        df['macd'] = 0
        df['signal'] = 0
        return df

    def signal(self, row: pd.Series, params: Dict[str, Any]) -> str:
        if row['rsi'] < 30 and row['macd'] > row['signal']:
            return 'LONG'
        if row['rsi'] > 70 and row['macd'] < row['signal']:
            return 'SHORT'
        return 'FLAT'

class BBRSI(StrategyTemplate):
    @property
    def required_timeframes(self) -> List[str]:
        # Example that might use 15m too, making it ineligible for HONG phase 0 unless strictly configured
        # Let's say it needs 15m
        return ["15m"] 

    def compute_features(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        df = data.get("15m", pd.DataFrame()).copy()
        return df

    def signal(self, row: pd.Series, params: Dict[str, Any]) -> str:
        return 'FLAT'
