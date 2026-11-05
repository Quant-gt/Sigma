# apps/engine/scanner/indicators.py
# High-Performance Rolling Technical Indicators (NumPy / Numba Compatible)

import numpy as np
from typing import Tuple


def compute_ema(prices: np.ndarray, period: int) -> float:
    """Computes Exponential Moving Average on the latest bar."""
    if len(prices) < period:
        return float(prices[-1]) if len(prices) > 0 else 0.0
    k = 2.0 / (period + 1.0)
    ema = float(prices[0])
    for price in prices[1:]:
        ema = (float(price) * k) + (ema * (1.0 - k))
    return round(ema, 2)


def compute_rsi(prices: np.ndarray, period: int = 14) -> float:
    """Computes standard Wilder's Relative Strength Index (0 to 100)."""
    if len(prices) <= period:
        return 50.0

    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    # Wilder smoothing
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(float(rsi), 2)


def compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    """Computes Average True Range."""
    if len(closes) <= period:
        return float(highs[-1] - lows[-1]) if len(highs) > 0 else 0.0

    tr1 = highs[1:] - lows[1:]
    tr2 = np.abs(highs[1:] - closes[:-1])
    tr3 = np.abs(lows[1:] - closes[:-1])
    tr = np.maximum(tr1, np.maximum(tr2, tr3))

    atr = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr = (atr * (period - 1) + tr[i]) / period
    return round(float(atr), 2)


def compute_supertrend(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    period: int = 10,
    multiplier: float = 3.0
) -> Tuple[float, int]:
    """
    Computes SuperTrend indicator line and trend direction (+1 Bullish, -1 Bearish).
    Returns (supertrend_value, direction)
    """
    if len(closes) < period:
        return float(closes[-1]) if len(closes) > 0 else 0.0, 1

    atr = compute_atr(highs, lows, closes, period)
    hl2 = (highs[-1] + lows[-1]) / 2.0
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)

    curr_close = closes[-1]
    if curr_close > basic_upper:
        return round(float(basic_lower), 2), 1
    elif curr_close < basic_lower:
        return round(float(basic_upper), 2), -1
    else:
        return round(float(hl2), 2), 1


def compute_vwap(prices: np.ndarray, volumes: np.ndarray) -> float:
    """Computes Volume Weighted Average Price."""
    total_volume = np.sum(volumes)
    if total_volume == 0:
        return float(prices[-1]) if len(prices) > 0 else 0.0
    vwap = np.sum(prices * volumes) / total_volume
    return round(float(vwap), 2)
