from dataclasses import dataclass
from typing import List

@dataclass
class PanelSpec:
    freq: str
    symbols: List[str]
    start: str
    end: str
    source: str = "derived"

    def __post_init__(self):
        if not self.symbols:
            raise ValueError("symbols list cannot be empty")
        valid_freqs = ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"]
        if self.freq not in valid_freqs:
            raise ValueError(f"freq must be one of {valid_freqs}")
