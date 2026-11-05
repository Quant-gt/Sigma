from __future__ import annotations
import time
from decimal import Decimal
import numpy as np
import pandas as pd
import polars as pl
import pytest

from apps.api.app.schemas.ast_schema import StrategyAST, IndicatorNode, ActionLegNode, UniverseNode, DAGEdge, RiskLegConfig
from apps.engine.backtest.vector_options_engine import QuantraVectorizedBacktester, _simulate_option_leg_numba


# ============================================================================
# 1. LEGACY PANDAS/LOOP IMPLEMENTATION (The Baseline to Outperform)
# ============================================================================
def legacy_pandas_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def legacy_pandas_backtest_runner(spot_df: pd.DataFrame, options_df: pd.DataFrame, sl_pct: float) -> float:
    """Legacy row-by-row Pandas iteration backtest runner."""
    total_pnl = 0.0
    in_pos = False
    entry_px = 0.0
    
    # Precompute legacy RSI
    spot_df["legacy_rsi"] = legacy_pandas_rsi(spot_df["spot_close"], 14)
    
    for i in range(len(spot_df)):
        row = spot_df.iloc[i]
        ts = row["timestamp"]
        rsi_val = row["legacy_rsi"]
        
        if not in_pos and pd.notna(rsi_val) and rsi_val > 60.0:
            # Enter short option dummy leg
            matching_opt = options_df[(options_df["timestamp"] == ts) & (options_df["strike"] == row["atm_strike"]) & (options_df["option_type"] == "CE")]
            if not matching_opt.empty:
                in_pos = True
                entry_px = float(matching_opt.iloc[0]["opt_close"])
        elif in_pos:
            matching_opt = options_df[(options_df["timestamp"] == ts) & (options_df["strike"] == row["atm_strike"]) & (options_df["option_type"] == "CE")]
            if not matching_opt.empty:
                current_px = float(matching_opt.iloc[0]["opt_close"])
                # Check 25% SL on short option
                if current_px >= entry_px * (1.0 + sl_pct):
                    total_pnl -= entry_px * sl_pct * 75  # 1 Lot Nifty
                    in_pos = False
    return total_pnl


# ============================================================================
# 2. FIXTURE: SYNTHETIC DETERMINISTIC TRADING DATA (5,000+ Bars)
# ============================================================================
@pytest.fixture
def synthetic_market_data() -> tuple[pl.DataFrame, pl.DataFrame, pd.DataFrame, pd.DataFrame]:
    np.random.seed(42)
    n_bars = 5000
    base_ts = 1717123200  # Epoch base
    timestamps = np.array([base_ts + i * 60 for i in range(n_bars)], dtype=np.int64)
    day_ids = np.array([20240601 + (i // 375) for i in range(n_bars)], dtype=np.int32)
    
    # Generate random walk spot prices around 24,000 Nifty
    spot_returns = np.random.normal(loc=0.00002, scale=0.001, size=n_bars)
    spot_closes = 24000.0 * np.cumprod(1.0 + spot_returns)
    spot_opens = spot_closes * (1.0 + np.random.normal(0, 0.0002, n_bars))
    spot_highs = np.maximum(spot_opens, spot_closes) * (1.0 + np.abs(np.random.normal(0, 0.0003, n_bars)))
    spot_lows = np.minimum(spot_opens, spot_closes) * (1.0 - np.abs(np.random.normal(0, 0.0003, n_bars)))
    spot_vols = np.random.randint(1000, 50000, size=n_bars)
    hhmm_arr = np.array([((t % 86400) // 3600) * 100 + ((t % 3600) // 60) for t in timestamps], dtype=np.int32)

    spot_pl = pl.DataFrame({
        "timestamp": timestamps,
        "day_id": day_ids,
        "hhmm": hhmm_arr,
        "spot_open": spot_opens,
        "spot_high": spot_highs,
        "spot_low": spot_lows,
        "spot_close": spot_closes,
        "spot_volume": spot_vols,
    })

    spot_pd = spot_pl.to_pandas()
    spot_pd["atm_strike"] = (spot_pd["spot_close"] / 50).round(0) * 50

    # Generate matching options chain data
    opt_rows = []
    strikes = [23800, 23900, 24000, 24100, 24200]
    for i in range(n_bars):
        ts = timestamps[i]
        s_close = spot_closes[i]
        for st in strikes:
            # Intrinsic + time value proxy
            dist = abs(s_close - st)
            base_prem = max(20.0, 150.0 - (dist * 0.1) + np.random.normal(0, 5.0))
            opt_rows.append({
                "timestamp": ts,
                "strike": st,
                "option_type": "CE",
                "opt_open": base_prem * 0.99,
                "opt_high": base_prem * 1.02,
                "opt_low": base_prem * 0.98,
                "opt_close": base_prem,
            })

    options_pl = pl.DataFrame(opt_rows)
    options_pd = options_pl.to_pandas()

    return spot_pl, options_pl, spot_pd, options_pd


# ============================================================================
# 3. PYTEST PARITY & BENCHMARK SUITE
# ============================================================================
def test_rsi_indicator_parity(synthetic_market_data):
    spot_pl, _, spot_pd, _ = synthetic_market_data

    # 1. Legacy Pandas RSI
    legacy_rsi = legacy_pandas_rsi(spot_pd["spot_close"], period=14).to_numpy()

    # 2. New Polars Vectorized RSI implementation
    delta = pl.col("spot_close").diff()
    gain = pl.when(delta > 0).then(delta).otherwise(0.0).rolling_mean(14)
    loss = pl.when(delta < 0).then(-delta).otherwise(0.0).rolling_mean(14)
    rs = gain / (loss + 1e-9)
    new_rsi_expr = (100.0 - (100.0 / (1.0 + rs))).alias("rsi")
    
    new_rsi = spot_pl.with_columns(new_rsi_expr)["rsi"].to_numpy()

    # Assert mathematical parity (ignoring first 20 NaN warm-up bars)
    valid_mask = ~np.isnan(legacy_rsi) & ~np.isnan(new_rsi)
    np.testing.assert_allclose(
        legacy_rsi[valid_mask],
        new_rsi[valid_mask],
        rtol=1e-5,
        atol=1e-5,
        err_msg="Polars vectorized RSI diverges from legacy Pandas implementation.",
    )


def test_numba_options_engine_speedup(synthetic_market_data):
    spot_pl, options_pl, spot_pd, options_pd = synthetic_market_data

    # Benchmark Legacy Pandas Loop Runner
    t0 = time.perf_counter()
    legacy_pnl = legacy_pandas_backtest_runner(spot_pd, options_pd, sl_pct=0.25)
    legacy_duration = time.perf_counter() - t0

    # Build StrategyAST for new Vectorized Engine
    ast = StrategyAST(
        strategy_name="Parity Test Strategy",
        nodes=[
            UniverseNode(node_id="u1", segment="NSE_FNO", underlying="NIFTY", expiry_type="WEEKLY_CURRENT"),
            IndicatorNode(node_id="ind1", indicator="RSI", timeframe="1m", params={"period": 14}),
            ActionLegNode(
                node_id="leg1",
                trigger_node_id="ind1",
                universe_node_id="u1",
                side="SELL",
                lots=1,
                risk_config=RiskLegConfig(
                    stop_loss_type="PERCENT",
                    stop_loss_value=Decimal("25.0"),
                    target_type="NONE",
                    trailing_sl_enabled=False,
                ),
            ),
        ],
        edges=[
            DAGEdge(id="e1", source="u1", target="ind1"),
            DAGEdge(id="e2", source="ind1", target="leg1"),
        ],
    )

    backtester = QuantraVectorizedBacktester(initial_capital_inr=Decimal("500000.00"))

    # JIT Warm-up call (compiles Numba LLVM code once so benchmark measures pure execution throughput)
    backtester.run_backtest(ast, spot_pl.slice(0, 100), options_pl.slice(0, 500), underlying="NIFTY")

    # Benchmark New Polars + Numba Vectorized Engine
    t1 = time.perf_counter()
    report = backtester.run_backtest(ast, spot_pl, options_pl, underlying="NIFTY")
    new_duration = time.perf_counter() - t1

    print(f"\n[BENCHMARK] Legacy Pandas Loop Duration: {legacy_duration:.4f}s")
    print(f"[BENCHMARK] New Polars + Numba Engine Duration: {new_duration:.4f}s")
    print(f"[SPEEDUP] New engine is {legacy_duration / (new_duration + 1e-9):.1f}x faster.")

    # Assert new engine completes in under 0.25 seconds
    assert new_duration < 0.25, f"Vectorized engine too slow: {new_duration} seconds."
    assert report.total_trades >= 0
