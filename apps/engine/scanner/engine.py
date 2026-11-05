# apps/engine/scanner/engine.py
from __future__ import annotations
import asyncio
from collections import deque
from dataclasses import dataclass, field
import json
import time
from typing import Callable, Deque, Dict, List
import redis.asyncio as aioredis


@dataclass
class OHLCVCandle:
    bucket_ts: int
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class SymbolRollingState:
    symbol: str
    candles_1m: Deque[OHLCVCandle] = field(default_factory=lambda: deque(maxlen=200))
    candles_5m: Deque[OHLCVCandle] = field(default_factory=lambda: deque(maxlen=200))
    # Incremental O(1) indicators
    ema_20: float = 0.0
    ema_50: float = 0.0
    rsi_avg_gain: float = 0.0
    rsi_avg_loss: float = 0.0
    rsi_14: float = 50.0
    cum_pv_today: float = 0.0
    cum_vol_today: int = 0
    vwap: float = 0.0
    prev_close: float = 0.0

    def update_on_tick(self, ltp: float, last_traded_qty: int, epoch_sec: int) -> bool:
        """
        Updates 1m & 5m candles and incremental VWAP/EMA/RSI in O(1) time.
        Returns True if a 1-minute candle just closed.
        """
        bucket_1m = (epoch_sec // 60) * 60
        candle_closed = False

        # Update Daily Intraday VWAP
        self.cum_pv_today += ltp * last_traded_qty
        self.cum_vol_today += last_traded_qty
        if self.cum_vol_today > 0:
            self.vwap = self.cum_pv_today / self.cum_vol_today

        if not self.candles_1m or self.candles_1m[-1].bucket_ts != bucket_1m:
            if self.candles_1m:
                candle_closed = True
                self._recompute_closed_candle_indicators(self.candles_1m[-1].close)
            self.candles_1m.append(
                OHLCVCandle(
                    bucket_ts=bucket_1m,
                    open=ltp,
                    high=ltp,
                    low=ltp,
                    close=ltp,
                    volume=last_traded_qty,
                )
            )
        else:
            curr = self.candles_1m[-1]
            if ltp > curr.high:
                curr.high = ltp
            if ltp < curr.low:
                curr.low = ltp
            curr.close = ltp
            curr.volume += last_traded_qty

        return candle_closed

    def _recompute_closed_candle_indicators(self, closed_px: float) -> None:
        # 1. Incremental EMA(20) and EMA(50)
        if self.ema_20 == 0.0:
            self.ema_20 = closed_px
            self.ema_50 = closed_px
        else:
            k20 = 2.0 / 21.0
            k50 = 2.0 / 51.0
            self.ema_20 = (closed_px - self.ema_20) * k20 + self.ema_20
            self.ema_50 = (closed_px - self.ema_50) * k50 + self.ema_50

        # 2. Wilder's Incremental RSI(14)
        if self.prev_close > 0.0:
            diff = closed_px - self.prev_close
            gain = max(0.0, diff)
            loss = max(0.0, -diff)
            self.rsi_avg_gain = ((self.rsi_avg_gain * 13.0) + gain) / 14.0
            self.rsi_avg_loss = ((self.rsi_avg_loss * 13.0) + loss) / 14.0
            if self.rsi_avg_loss == 0:
                self.rsi_14 = 100.0
            else:
                rs = self.rsi_avg_gain / self.rsi_avg_loss
                self.rsi_14 = 100.0 - (100.0 / (1.0 + rs))
        self.prev_close = closed_px


class Nifty500RealTimeScanner:
    """
    Consumes normalized broker ticks from Redis Streams (`quantra:ticks:stream`),
    evaluates registered user scanner predicates across Nifty 500 in < 10ms,
    and publishes live alerts to `quantra:scanner:alerts`.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.states: Dict[str, SymbolRollingState] = {}
        self.active_scanners: Dict[str, Callable[[SymbolRollingState], bool]] = {
            "BULLISH_VWAP_RSI_BREAKOUT": lambda s: (
                len(s.candles_1m) > 15
                and s.candles_1m[-1].close > s.vwap
                and s.ema_20 > s.ema_50
                and s.rsi_14 > 60.0
            ),
            "BEARISH_INTRADAY_DUMP": lambda s: (
                len(s.candles_1m) > 15
                and s.candles_1m[-1].close < s.vwap
                and s.ema_20 < s.ema_50
                and s.rsi_14 < 35.0
            ),
        }

    async def run_forever(self, consumer_group: str = "scanner-cg", worker_id: str = "scanner-1"):
        stream_key = "quantra:ticks:stream"
        try:
            await self.redis.xgroup_create(stream_key, consumer_group, id="0", mkstream=True)
        except Exception:
            pass  # Group already exists

        while True:
            entries = await self.redis.xreadgroup(
                groupname=consumer_group,
                consumername=worker_id,
                streams={stream_key: ">"},
                count=500,
                block=50,
            )
            if not entries:
                continue

            ack_ids: List[str] = []
            for _, messages in entries:
                for msg_id, fields in messages:
                    ack_ids.append(msg_id)
                    symbol = fields[b"symbol"].decode("utf-8")
                    ltp = float(fields[b"ltp"])
                    ltq = int(fields[b"ltq"])
                    ts = int(fields[b"ts"])

                    state = self.states.get(symbol)
                    if state is None:
                        state = SymbolRollingState(symbol=symbol)
                        self.states[symbol] = state

                    state.update_on_tick(ltp, ltq, ts)

                    # Evaluate active scanners on every tick
                    for scan_id, predicate in self.active_scanners.items():
                        if predicate(state):
                            alert_payload = {
                                "scanner_id": scan_id,
                                "symbol": symbol,
                                "ltp": round(ltp, 2),
                                "vwap": round(state.vwap, 2),
                                "rsi_14": round(state.rsi_14, 2),
                                "ema_20": round(state.ema_20, 2),
                                "timestamp": int(time.time() * 1000),
                            }
                            await self.redis.publish(
                                "quantra:scanner:alerts", json.dumps(alert_payload)
                            )

            if ack_ids:
                await self.redis.xack(stream_key, consumer_group, *ack_ids)
