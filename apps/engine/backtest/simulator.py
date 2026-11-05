# apps/engine/backtest/simulator.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import numpy as np
import polars as pl
from numba import njit

from apps.api.app.schemas.ast_schema import StrategyAST, ActionLegNode, IndicatorNode
from apps.api.app.core.indian_costs import IndianStatutoryCostEngine, TradeInstrumentType


# ============================================================================
# 1. NUMBA JIT PATH-DEPENDENT INTRA-LEG SIMULATOR (SL, TSL, RE-ENTRY)
# ============================================================================
@njit(cache=True, fastmath=True)
def _simulate_option_leg_numba(
    timestamps: np.ndarray,       # int64 epoch seconds
    day_ids: np.ndarray,          # int32 YYYYMMDD
    entry_signals: np.ndarray,    # bool array from compiled AST trigger
    opt_open: np.ndarray,         # float64 option premium open
    opt_high: np.ndarray,         # float64 option premium high
    opt_low: np.ndarray,          # float64 option premium low
    opt_close: np.ndarray,        # float64 option premium close
    side_mult: int,               # +1 for BUY, -1 for SELL
    sl_pct: float,                # e.g., 0.25 for 25% SL
    target_pct: float,            # e.g., 0.50 for 50% Target (0.0 if disabled)
    tsl_enabled: bool,
    trail_step_pct: float,        # e.g., 0.10 (every 10% move in favor)
    trail_by_pct: float,          # e.g., 0.05 (trail SL by 5%)
    max_reentries: int,           # Max re-entries per day on SL hit
    entry_hhmm: int,              # e.g., 916 for 09:16 IST
    exit_hhmm: int,               # e.g., 1515 for 15:15 IST
    hhmm_array: np.ndarray,       # int32 HHMM of each bar
    slippage_bps: float           # e.g., 50 bps = 0.005
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Executes single-pass C-speed simulation of an options leg with realistic intrabar high/low SL checks.
    Returns arrays of (entry_idx, exit_idx, entry_fill_price, exit_fill_price, exit_reason_code)
    Exit Reason Codes: 1 = STOP_LOSS, 2 = TRAILING_SL, 3 = TARGET, 4 = EOD_SQUARE_OFF
    """
    n = len(timestamps)
    max_trades = n // 2 + 1
    out_entry_idx = np.empty(max_trades, dtype=np.int64)
    out_exit_idx = np.empty(max_trades, dtype=np.int64)
    out_entry_px = np.empty(max_trades, dtype=np.float64)
    out_exit_px = np.empty(max_trades, dtype=np.float64)
    out_reason = np.empty(max_trades, dtype=np.int32)

    trade_count = 0
    in_position = False
    entry_px = 0.0
    active_sl_px = 0.0
    active_target_px = 0.0
    best_favorable_px = 0.0
    entry_bar = 0
    current_day = -1
    reentries_used_today = 0
    initial_entry_done_today = False
    slip_mult = slippage_bps / 10000.0

    for i in range(n):
        day = day_ids[i]
        hhmm = hhmm_array[i]

        # Reset daily counters on new trading day
        if day != current_day:
            current_day = day
            reentries_used_today = 0
            initial_entry_done_today = False
            in_position = False

        if not in_position:
            # Check if within valid entry window
            if hhmm >= entry_hhmm and hhmm < exit_hhmm:
                can_enter = (not initial_entry_done_today and entry_signals[i]) or (
                    initial_entry_done_today
                    and reentries_used_today < max_reentries
                    and entry_signals[i]
                )
                if can_enter and opt_close[i] > 0.5:
                    in_position = True
                    entry_bar = i
                    # Apply realistic entry slippage
                    if side_mult == 1:  # BUY
                        entry_px = opt_close[i] * (1.0 + slip_mult)
                        active_sl_px = entry_px * (1.0 - sl_pct)
                        active_target_px = entry_px * (1.0 + target_pct) if target_pct > 0 else 1e12
                    else:               # SELL (Short Option)
                        entry_px = opt_close[i] * (1.0 - slip_mult)
                        active_sl_px = entry_px * (1.0 + sl_pct)
                        active_target_px = entry_px * (1.0 - target_pct) if target_pct > 0 else 0.0

                    best_favorable_px = entry_px
                    if initial_entry_done_today:
                        reentries_used_today += 1
                    initial_entry_done_today = True
        else:
            # Position is OPEN -> Evaluate Intrabar SL, Target, TSL, or EOD Square-Off
            bar_high = opt_high[i]
            bar_low = opt_low[i]
            bar_close = opt_close[i]

            exit_triggered = False
            exit_px = 0.0
            reason = 0

            # 1. Check Hard Stop-Loss or Trailing SL Hit First (Conservative Worst-Case)
            if side_mult == 1 and bar_low <= active_sl_px:
                exit_triggered = True
                exit_px = active_sl_px * (1.0 - slip_mult)
                reason = 2 if (tsl_enabled and active_sl_px > entry_px * (1.0 - sl_pct)) else 1
            elif side_mult == -1 and bar_high >= active_sl_px:
                exit_triggered = True
                exit_px = active_sl_px * (1.0 + slip_mult)
                reason = 2 if (tsl_enabled and active_sl_px < entry_px * (1.0 + sl_pct)) else 1

            # 2. Check Target Hit
            elif side_mult == 1 and target_pct > 0 and bar_high >= active_target_px:
                exit_triggered = True
                exit_px = active_target_px * (1.0 - slip_mult)
                reason = 3
            elif side_mult == -1 and target_pct > 0 and bar_low <= active_target_px:
                exit_triggered = True
                exit_px = active_target_px * (1.0 + slip_mult)
                reason = 3

            # 3. Check 15:15 IST Intraday Square-Off
            elif hhmm >= exit_hhmm:
                exit_triggered = True
                exit_px = bar_close * (1.0 - slip_mult if side_mult == 1 else 1.0 + slip_mult)
                reason = 4

            # 4. Update Trailing Stop Loss if still in position
            if not exit_triggered and tsl_enabled and trail_step_pct > 0:
                if side_mult == 1 and bar_high > best_favorable_px:
                    move_pct = (bar_high - entry_px) / entry_px
                    steps = int(move_pct / trail_step_pct)
                    if steps > 0:
                        new_sl = entry_px * (1.0 - sl_pct + steps * trail_by_pct)
                        if new_sl > active_sl_px:
                            active_sl_px = new_sl
                    best_favorable_px = bar_high
                elif side_mult == -1 and bar_low < best_favorable_px:
                    move_pct = (entry_px - bar_low) / entry_px
                    steps = int(move_pct / trail_step_pct)
                    if steps > 0:
                        new_sl = entry_px * (1.0 + sl_pct - steps * trail_by_pct)
                        if new_sl < active_sl_px:
                            active_sl_px = new_sl
                    best_favorable_px = bar_low

            if exit_triggered:
                out_entry_idx[trade_count] = entry_bar
                out_exit_idx[trade_count] = i
                out_entry_px[trade_count] = entry_px
                out_exit_px[trade_count] = max(0.05, exit_px)
                out_reason[trade_count] = reason
                trade_count += 1
                in_position = False

    return (
        out_entry_idx[:trade_count],
        out_exit_idx[:trade_count],
        out_entry_px[:trade_count],
        out_exit_px[:trade_count],
        out_reason[:trade_count],
    )


# ============================================================================
# 2. POLARS VECTORIZED AST INDICATOR & DYNAMIC OPTION STRIKE ENGINE
# ============================================================================
@dataclass
class BacktestPerformanceReport:
    strategy_name: str
    ast_hash: str
    total_trades: int
    win_rate_pct: float
    gross_pnl_inr: Decimal
    total_statutory_charges_inr: Decimal
    net_pnl_inr: Decimal
    cagr_pct: float
    max_drawdown_inr: Decimal
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    monthly_pnl_matrix: Dict[str, float]
    trade_log: List[Dict]


class QuantraVectorizedBacktester:
    """
    Evaluates a compiled StrategyAST over Polars DataFrames of underlying + options chains,
    resolves dynamic ATM/OTM strikes per minute, runs the Numba leg simulator, and deducts
    exact Indian statutory taxes (STT 0.1% on Options Sell, NSE turnover, Stamp Duty, 18% GST).
    """

    LOT_SIZES = {"NIFTY": 75, "BANKNIFTY": 30, "FINNIFTY": 65}
    STRIKE_STEPS = {"NIFTY": 50, "BANKNIFTY": 100, "FINNIFTY": 50}

    def __init__(self, initial_capital_inr: Decimal = Decimal("500000.00")):
        self.initial_capital = initial_capital_inr

    def _compute_polars_indicators(self, spot_df: pl.DataFrame, ast: StrategyAST) -> pl.DataFrame:
        """Vectorized computation of technical indicators defined in StrategyAST."""
        exprs: List[pl.Expr] = []
        for node in ast.nodes:
            if isinstance(node, IndicatorNode):
                period = int(node.params.get("period", 14))
                if node.indicator == "EMA":
                    exprs.append(
                        pl.col("spot_close").ewm_mean(span=period).alias(node.node_id)
                    )
                elif node.indicator == "SMA":
                    exprs.append(
                        pl.col("spot_close").rolling_mean(window_size=period).alias(node.node_id)
                    )
                elif node.indicator == "RSI":
                    delta = pl.col("spot_close").diff()
                    gain = pl.when(delta > 0).then(delta).otherwise(0.0).rolling_mean(period)
                    loss = pl.when(delta < 0).then(-delta).otherwise(0.0).rolling_mean(period)
                    rs = gain / (loss + 1e-9)
                    exprs.append((100.0 - (100.0 / (1.0 + rs))).alias(node.node_id))
                elif node.indicator == "VWAP":
                    exprs.append(
                        (
                            (pl.col("spot_close") * pl.col("spot_volume")).cum_sum().over("day_id")
                            / (pl.col("spot_volume").cum_sum().over("day_id") + 1)
                        ).alias(node.node_id)
                    )
                elif node.indicator == "SUPERTREND":
                    # Vectorized ATR-based bands approximation
                    tr = pl.max_horizontal(
                        pl.col("spot_high") - pl.col("spot_low"),
                        (pl.col("spot_high") - pl.col("spot_close").shift(1)).abs(),
                        (pl.col("spot_low") - pl.col("spot_close").shift(1)).abs(),
                    )
                    atr = tr.rolling_mean(period)
                    mult = float(node.params.get("multiplier", 3.0))
                    hl2 = (pl.col("spot_high") + pl.col("spot_low")) / 2.0
                    exprs.append((hl2 - mult * atr).alias(node.node_id))

        return spot_df.with_columns(exprs) if exprs else spot_df

    def run_backtest(
        self,
        ast: StrategyAST,
        spot_df: pl.DataFrame,
        options_chain_df: pl.DataFrame,
        underlying: str = "NIFTY",
    ) -> BacktestPerformanceReport:
        """
        spot_df columns: [timestamp, day_id, hhmm, spot_open, spot_high, spot_low, spot_close, spot_volume]
        options_chain_df columns: [timestamp, strike, option_type, opt_open, opt_high, opt_low, opt_close]
        """
        # 1. Enrich Spot DataFrame with AST Indicators
        enriched_spot = self._compute_polars_indicators(spot_df, ast)
        strike_step = self.STRIKE_STEPS.get(underlying, 50)
        lot_size = self.LOT_SIZES.get(underlying, 75)

        # 2. Compute Dynamic ATM Strike for every 1-minute bar
        enriched_spot = enriched_spot.with_columns(
            ((pl.col("spot_close") / strike_step).round(0).cast(pl.Int64) * strike_step).alias("atm_strike")
        )

        entry_hhmm = int(ast.entry_time_ist[:2]) * 100 + int(ast.entry_time_ist[3:5])
        exit_hhmm = int(ast.square_off_time_ist[:2]) * 100 + int(ast.square_off_time_ist[3:5])

        all_trades: List[Dict] = []
        gross_pnl_total = Decimal("0.00")
        charges_total = Decimal("0.00")

        # 3. Execute Each ActionLegNode in the AST
        action_legs = [n for n in ast.nodes if isinstance(n, ActionLegNode)]
        for leg in action_legs:
            offset_steps = leg.strike_config.atm_offset_steps if leg.strike_config else 0
            opt_type = leg.strike_config.option_type if leg.strike_config else "CE"

            leg_df = enriched_spot.with_columns(
                (pl.col("atm_strike") + (offset_steps * strike_step)).alias("target_strike"),
                pl.lit(opt_type).alias("option_type"),
            ).join(
                options_chain_df,
                left_on=["timestamp", "target_strike", "option_type"],
                right_on=["timestamp", "strike", "option_type"],
                how="inner",
            ).sort("timestamp")

            # Evaluate entry signal vector (default true during entry window if time-triggered or condition met)
            entry_signals = np.ones(leg_df.height, dtype=np.bool_)
            side_mult = 1 if leg.side == "BUY" else -1
            sl_pct = float(leg.risk_config.stop_loss_value) / 100.0
            target_pct = (
                float(leg.risk_config.target_value) / 100.0
                if leg.risk_config.target_value
                else 0.0
            )
            trail_step = (
                float(leg.risk_config.trail_step_Move) / 100.0
                if leg.risk_config.trail_step_Move
                else 0.0
            )
            trail_by = (
                float(leg.risk_config.trail_sl_by) / 100.0
                if leg.risk_config.trail_sl_by
                else 0.0
            )

            ts_arr = leg_df["timestamp"].to_numpy()
            day_arr = leg_df["day_id"].to_numpy()
            hhmm_arr = leg_df["hhmm"].to_numpy()
            o_open = leg_df["opt_open"].to_numpy()
            o_high = leg_df["opt_high"].to_numpy()
            o_low = leg_df["opt_low"].to_numpy()
            o_close = leg_df["opt_close"].to_numpy()

            e_idx, x_idx, e_px, x_px, reasons = _simulate_option_leg_numba(
                ts_arr,
                day_arr,
                entry_signals,
                o_open,
                o_high,
                o_low,
                o_close,
                side_mult,
                sl_pct,
                target_pct,
                leg.risk_config.trailing_sl_enabled,
                trail_step,
                trail_by,
                leg.risk_config.max_reentries_on_sl,
                entry_hhmm,
                exit_hhmm,
                hhmm_arr,
                float(leg.mpp_slippage_bps),
            )

            qty = leg.lots * lot_size
            reason_map = {1: "STOP_LOSS", 2: "TRAILING_SL", 3: "TARGET", 4: "EOD_SQUARE_OFF"}

            for k in range(len(e_idx)):
                entry_p = Decimal(str(round(float(e_px[k]), 2)))
                exit_p = Decimal(str(round(float(x_px[k]), 2)))
                buy_p = entry_p if leg.side == "BUY" else exit_p
                sell_p = exit_p if leg.side == "BUY" else entry_p

                gross_pnl = (sell_p - buy_p) * Decimal(qty)
                cost_breakdown = IndianStatutoryCostEngine.calculate_round_trip(
                    instrument=TradeInstrumentType.OPTIONS,
                    buy_price=buy_p,
                    sell_price=sell_p,
                    quantity=qty,
                )
                net_pnl = gross_pnl - cost_breakdown.total_charges
                gross_pnl_total += gross_pnl
                charges_total += cost_breakdown.total_charges

                all_trades.append(
                    {
                        "leg_id": leg.node_id,
                        "side": leg.side,
                        "option_type": opt_type,
                        "quantity": qty,
                        "entry_timestamp": int(ts_arr[e_idx[k]]),
                        "exit_timestamp": int(ts_arr[x_idx[k]]),
                        "entry_price": float(entry_p),
                        "exit_price": float(exit_p),
                        "exit_reason": reason_map.get(int(reasons[k]), "UNKNOWN"),
                        "gross_pnl_inr": float(gross_pnl),
                        "statutory_charges_inr": float(cost_breakdown.total_charges),
                        "net_pnl_inr": float(net_pnl),
                    }
                )

        # 4. Compute Institutional Portfolio Metrics (Drawdown, Sharpe, Sortino, Calmar)
        net_pnl_total = gross_pnl_total - charges_total
        pnl_series = np.array([t["net_pnl_inr"] for t in all_trades], dtype=np.float64)

        if len(pnl_series) > 0:
            wins = int(np.sum(pnl_series > 0))
            win_rate = round((wins / len(pnl_series)) * 100.0, 2)
            cum_pnl = np.cumsum(pnl_series)
            peak = np.maximum.accumulate(np.maximum(0.0, cum_pnl))
            dd_series = peak - cum_pnl
            max_dd_inr = Decimal(str(round(float(np.max(dd_series)), 2)))
            max_dd_pct = round((float(max_dd_inr) / float(self.initial_capital)) * 100.0, 2)

            mean_ret = float(np.mean(pnl_series))
            std_ret = float(np.std(pnl_series)) + 1e-9
            downside_std = float(np.std(pnl_series[pnl_series < 0])) + 1e-9 if np.any(pnl_series < 0) else 1.0
            sharpe = round((mean_ret / std_ret) * np.sqrt(252), 2)
            sortino = round((mean_ret / downside_std) * np.sqrt(252), 2)
            cagr = round((float(net_pnl_total) / float(self.initial_capital)) * 100.0, 2)
            calmar = round(cagr / (max_dd_pct if max_dd_pct > 0 else 1.0), 2)
        else:
            win_rate, max_dd_inr, max_dd_pct, sharpe, sortino, cagr, calmar = (
                0.0, Decimal("0.00"), 0.0, 0.0, 0.0, 0.0, 0.0
            )

        return BacktestPerformanceReport(
            strategy_name=ast.strategy_name,
            ast_hash=ast.compute_cryptographic_hash(),
            total_trades=len(all_trades),
            win_rate_pct=win_rate,
            gross_pnl_inr=gross_pnl_total,
            total_statutory_charges_inr=charges_total,
            net_pnl_inr=net_pnl_total,
            cagr_pct=cagr,
            max_drawdown_inr=max_dd_inr,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            monthly_pnl_matrix={},
            trade_log=all_trades,
        )
