# apps/engine/workers/tick_ingestor.py
# Broker WebSocket Tick Ingestor & Rolling OHLCV Aggregator (Redis Streams)

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import redis.asyncio as redis


@dataclass
class Candle:
    symbol: str
    timeframe: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int


class TickIngestor:
    """
    Normalizes incoming multi-broker binary tick feeds into standardized
    Redis Streams ('stream:ticks:normalized') and aggregates real-time 1m/3m/5m/15m OHLCV bars.
    """

    def __init__(self, redis_client: redis.Redis):
        self.r = redis_client
        self.active_candles: Dict[str, Dict[str, Candle]] = {}

    async def ingest_tick(self, symbol: str, ltp: float, volume: int, timestamp_ms: Optional[int] = None) -> None:
        ts = timestamp_ms or int(time.time() * 1000)

        # 1. Push normalized tick to Redis Stream with capped retention
        tick_data = {
            "symbol": symbol,
            "ltp": str(ltp),
            "volume": str(volume),
            "ts": str(ts),
        }
        await self.r.xadd("stream:ticks:normalized", tick_data, maxlen=50000, approximate=True)

        # 2. Update rolling candle bars
        for tf_minutes in (1, 3, 5, 15):
            tf_label = f"{tf_minutes}m"
            bucket_ts = (ts // (tf_minutes * 60 * 1000)) * (tf_minutes * 60 * 1000)
            candle_key = f"{symbol}:{tf_label}"

            current = self.active_candles.get(candle_key)
            if not current or current.timestamp != bucket_ts:
                # Flush completed previous candle to stream
                if current:
                    await self._publish_candle(current)

                # Initialize new candle bucket
                self.active_candles[candle_key] = Candle(
                    symbol=symbol,
                    timeframe=tf_label,
                    timestamp=bucket_ts,
                    open=ltp,
                    high=ltp,
                    low=ltp,
                    close=ltp,
                    volume=volume
                )
            else:
                # Update rolling high/low/close/volume
                current.high = max(current.high, ltp)
                current.low = min(current.low, ltp)
                current.close = ltp
                current.volume += volume

    async def _publish_candle(self, candle: Candle) -> None:
        payload = {
            "symbol": candle.symbol,
            "tf": candle.timeframe,
            "ts": str(candle.timestamp),
            "o": str(candle.open),
            "h": str(candle.high),
            "l": str(candle.low),
            "c": str(candle.close),
            "v": str(candle.volume)
        }
        await self.r.xadd(f"stream:candles:{candle.timeframe}", payload, maxlen=20000, approximate=True)
