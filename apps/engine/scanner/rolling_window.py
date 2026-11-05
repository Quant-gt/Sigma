# apps/engine/scanner/rolling_window.py
# High-Throughput In-Memory Rolling OHLCV Ring Buffer

from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import numpy as np


@dataclass(slots=True)
class OHLCVBar:
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class SymbolTimeframeBuffer:
    """Fixed-capacity ring buffer for a single (symbol, timeframe) pair."""

    def __init__(self, capacity: int = 250):
        self.capacity = capacity
        self.bars: deque[OHLCVBar] = deque(maxlen=capacity)

    def append(self, bar: OHLCVBar) -> None:
        if self.bars and self.bars[-1].timestamp == bar.timestamp:
            self.bars[-1] = bar  # Update in-progress candle
        else:
            self.bars.append(bar)

    def to_numpy(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Returns (opens, highs, lows, closes, volumes) as fast contiguous numpy arrays."""
        n = len(self.bars)
        if n == 0:
            empty = np.array([], dtype=np.float64)
            return empty, empty, empty, empty, np.array([], dtype=np.int64)

        highs = np.empty(n, dtype=np.float64)
        lows = np.empty(n, dtype=np.float64)
        closes = np.empty(n, dtype=np.float64)
        opens = np.empty(n, dtype=np.float64)
        volumes = np.empty(n, dtype=np.int64)

        for i, b in enumerate(self.bars):
            opens[i] = b.open
            highs[i] = b.high
            lows[i] = b.low
            closes[i] = b.close
            volumes[i] = b.volume

        return opens, highs, lows, closes, volumes


class MarketDataStore:
    """Global singleton holding rolling OHLCV buffers for all Nifty 500 & F&O contracts."""

    def __init__(self, buffer_capacity: int = 250):
        self.buffer_capacity = buffer_capacity
        # Key format: f"{symbol}:{timeframe}"
        self._buffers: Dict[str, SymbolTimeframeBuffer] = {}

    def get_or_create(self, symbol: str, timeframe: str) -> SymbolTimeframeBuffer:
        key = f"{symbol.upper()}:{timeframe}"
        if key not in self._buffers:
            self._buffers[key] = SymbolTimeframeBuffer(self.buffer_capacity)
        return self._buffers[key]

    def update_bar(
        self,
        symbol: str,
        timeframe: str,
        timestamp: int,
        o: float,
        h: float,
        l: float,
        c: float,
        v: int
    ) -> None:
        buf = self.get_or_create(symbol, timeframe)
        buf.append(OHLCVBar(timestamp=timestamp, open=o, high=h, low=l, close=c, volume=v))


# Global In-Memory Instance
market_store = MarketDataStore()
