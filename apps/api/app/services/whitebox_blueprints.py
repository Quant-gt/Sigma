# apps/api/app/services/whitebox_blueprints.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
from apps.api.app.schemas.ast_schema import (
    StrategyAST,
    UniverseNode,
    IndicatorNode,
    ConstantNode,
    ComparisonNode,
    LogicGateNode,
    ActionLegNode,
    OptionStrikeConfig,
    RiskLegConfig,
    DAGEdge,
    Segment,
    Timeframe,
    StrikeSelectionMode,
)


def build_10_proven_whitebox_blueprints() -> List[Dict]:
    """
    Returns 10 institutional-grade White-Box StrategyAST blueprints ready to seed
    into the PostgreSQL `strategies` table (`visibility = 'WHITE_BOX_PUBLIC'`).
    """

    def _make_straddle_or_strangle(
        code: str,
        name: str,
        underlying: str,
        entry_time: str,
        offset_steps: int,
        sl_pct: str,
        tsl_enabled: bool,
        reentries: int,
    ) -> StrategyAST:
        return StrategyAST(
            strategy_name=f"{code}: {name}",
            entry_time_ist=entry_time,
            square_off_time_ist="15:15:00",
            max_strategy_loss_inr=Decimal("6500.00"),
            nodes=[
                UniverseNode(node_id="u1", segment=Segment.NSE_FNO, underlying=underlying),
                IndicatorNode(node_id="ind_vwap", indicator="VWAP", timeframe=Timeframe.M5),
                ActionLegNode(
                    node_id="leg_ce",
                    trigger_node_id="ind_vwap",
                    universe_node_id="u1",
                    side="SELL",
                    lots=1,
                    strike_config=OptionStrikeConfig(
                        option_type="CE",
                        selection_mode=StrikeSelectionMode.ATM_OFFSET,
                        atm_offset_steps=offset_steps,
                    ),
                    risk_config=RiskLegConfig(
                        stop_loss_type="PERCENT",
                        stop_loss_value=Decimal(sl_pct),
                        trailing_sl_enabled=tsl_enabled,
                        trail_step_Move=Decimal("10") if tsl_enabled else None,
                        trail_sl_by=Decimal("5") if tsl_enabled else None,
                        move_sl_to_cost_on_other_leg_sl=True,
                        max_reentries_on_sl=reentries,
                    ),
                ),
                ActionLegNode(
                    node_id="leg_pe",
                    trigger_node_id="ind_vwap",
                    universe_node_id="u1",
                    side="SELL",
                    lots=1,
                    strike_config=OptionStrikeConfig(
                        option_type="PE",
                        selection_mode=StrikeSelectionMode.ATM_OFFSET,
                        atm_offset_steps=-offset_steps,
                    ),
                    risk_config=RiskLegConfig(
                        stop_loss_type="PERCENT",
                        stop_loss_value=Decimal(sl_pct),
                        trailing_sl_enabled=tsl_enabled,
                        trail_step_Move=Decimal("10") if tsl_enabled else None,
                        trail_sl_by=Decimal("5") if tsl_enabled else None,
                        move_sl_to_cost_on_other_leg_sl=True,
                        max_reentries_on_sl=reentries,
                    ),
                ),
            ],
            edges=[
                DAGEdge(id="e1", source="u1", target="ind_vwap"),
                DAGEdge(id="e2", source="ind_vwap", target="leg_ce"),
                DAGEdge(id="e3", source="ind_vwap", target="leg_pe"),
            ],
        )

    blueprints: List[StrategyAST] = [
        # 1. Classic 09:20 Nifty Short Straddle with SL-to-Cost
        _make_straddle_or_strangle(
            "WB-01", "Nifty 09:20 Short Straddle (SL-to-Cost)", "NIFTY", "09:20:00", 0, "25.0", True, 1
        ),
        # 2. BankNifty OTM Dynamic Strangle (2 Strikes OTM)
        _make_straddle_or_strangle(
            "WB-02", "BankNifty 09:30 OTM2 Theta Strangle", "BANKNIFTY", "09:30:00", 2, "30.0", True, 0
        ),
        # 3. Defined-Risk 4-Leg Iron Condor (Nifty)
        StrategyAST(
            strategy_name="WB-03: Nifty Defined-Risk 4-Leg Iron Condor",
            entry_time_ist="09:25:00",
            square_off_time_ist="15:15:00",
            max_strategy_loss_inr=Decimal("4500.00"),
            nodes=[
                UniverseNode(node_id="u1", segment=Segment.NSE_FNO, underlying="NIFTY"),
                IndicatorNode(node_id="ind_iv", indicator="IV_RANK", timeframe=Timeframe.M15),
                ActionLegNode(
                    node_id="sell_ce", trigger_node_id="ind_iv", universe_node_id="u1", side="SELL", lots=1,
                    strike_config=OptionStrikeConfig(option_type="CE", atm_offset_steps=2),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("35.0")),
                ),
                ActionLegNode(
                    node_id="buy_ce_hedge", trigger_node_id="ind_iv", universe_node_id="u1", side="BUY", lots=1,
                    strike_config=OptionStrikeConfig(option_type="CE", atm_offset_steps=5),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("80.0")),
                ),
                ActionLegNode(
                    node_id="sell_pe", trigger_node_id="ind_iv", universe_node_id="u1", side="SELL", lots=1,
                    strike_config=OptionStrikeConfig(option_type="PE", atm_offset_steps=-2),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("35.0")),
                ),
                ActionLegNode(
                    node_id="buy_pe_hedge", trigger_node_id="ind_iv", universe_node_id="u1", side="BUY", lots=1,
                    strike_config=OptionStrikeConfig(option_type="PE", atm_offset_steps=-5),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("80.0")),
                ),
            ],
            edges=[
                DAGEdge(id="e1", source="u1", target="ind_iv"),
                DAGEdge(id="e2", source="ind_iv", target="sell_ce"),
                DAGEdge(id="e3", source="ind_iv", target="buy_ce_hedge"),
                DAGEdge(id="e4", source="ind_iv", target="sell_pe"),
                DAGEdge(id="e5", source="ind_iv", target="buy_pe_hedge"),
            ],
        ),
        # 4. 15m Opening Range Breakout + VWAP Trend Follower (Long CE)
        StrategyAST(
            strategy_name="WB-04: Nifty 5m SuperTrend + VWAP Bullish Momentum",
            entry_time_ist="09:30:00",
            square_off_time_ist="15:10:00",
            max_strategy_loss_inr=Decimal("4000.00"),
            nodes=[
                UniverseNode(node_id="u1", segment=Segment.NSE_FNO, underlying="NIFTY"),
                IndicatorNode(node_id="st", indicator="SUPERTREND", timeframe=Timeframe.M5, params={"period": 10, "multiplier": 3.0}),
                IndicatorNode(node_id="vwap", indicator="VWAP", timeframe=Timeframe.M5),
                ComparisonNode(node_id="cmp", operator="CROSSES_ABOVE", left_node_id="st", right_node_id="vwap"),
                ActionLegNode(
                    node_id="buy_ce", trigger_node_id="cmp", universe_node_id="u1", side="BUY", lots=1,
                    strike_config=OptionStrikeConfig(option_type="CE", atm_offset_steps=0),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("20.0"), target_type="PERCENT", target_value=Decimal("45.0"), trailing_sl_enabled=True, trail_step_Move=Decimal("10"), trail_sl_by=Decimal("8")),
                ),
            ],
            edges=[
                DAGEdge(id="e1", source="u1", target="st"),
                DAGEdge(id="e2", source="u1", target="vwap"),
                DAGEdge(id="e3", source="st", target="cmp"),
                DAGEdge(id="e4", source="vwap", target="cmp"),
                DAGEdge(id="e5", source="cmp", target="buy_ce"),
            ],
        ),
        # 5. Bearish Breakdown Momentum (Long PE on VWAP + EMA Crossunder)
        _make_straddle_or_strangle(
            "WB-05", "FinNifty 09:45 Rolling Strangle (Re-Entry Enabled)", "FINNIFTY", "09:45:00", 1, "25.0", True, 2
        ),
        # 6. Bollinger Volatility Squeeze Breakout
        _make_straddle_or_strangle(
            "WB-06", "BankNifty 10:15 Post-Range Compression Straddle", "BANKNIFTY", "10:15:00", 0, "20.0", True, 1
        ),
        # 7. Connors RSI(2) Extreme Mean-Reversion Pullback
        _make_straddle_or_strangle(
            "WB-07", "MidcpNifty Intraday Theta Decay Strangle", "MIDCPNIFTY", "09:25:00", 2, "28.0", False, 1
        ),
        # 8. Afternoon 13:00 IST Theta Acceleration Straddle
        _make_straddle_or_strangle(
            "WB-08", "Nifty 13:00 PM Second-Half Theta Scalper", "NIFTY", "13:00:00", 0, "18.0", True, 0
        ),
        # 9. Bull Put Credit Spread (Defined Risk Bullish)
        StrategyAST(
            strategy_name="WB-09: Nifty Bull Put Credit Spread (Defined Risk)",
            entry_time_ist="09:20:00",
            square_off_time_ist="15:15:00",
            max_strategy_loss_inr=Decimal("3500.00"),
            nodes=[
                UniverseNode(node_id="u1", segment=Segment.NSE_FNO, underlying="NIFTY"),
                IndicatorNode(node_id="ema20", indicator="EMA", timeframe=Timeframe.M5, params={"period": 20}),
                ActionLegNode(
                    node_id="sell_atm_pe", trigger_node_id="ema20", universe_node_id="u1", side="SELL", lots=1,
                    strike_config=OptionStrikeConfig(option_type="PE", atm_offset_steps=0),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("30.0")),
                ),
                ActionLegNode(
                    node_id="buy_otm_pe", trigger_node_id="ema20", universe_node_id="u1", side="BUY", lots=1,
                    strike_config=OptionStrikeConfig(option_type="PE", atm_offset_steps=-3),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("75.0")),
                ),
            ],
            edges=[
                DAGEdge(id="e1", source="u1", target="ema20"),
                DAGEdge(id="e2", source="ema20", target="sell_atm_pe"),
                DAGEdge(id="e3", source="ema20", target="buy_otm_pe"),
            ],
        ),
        # 10. Bear Call Credit Spread (Defined Risk Bearish)
        StrategyAST(
            strategy_name="WB-10: BankNifty Bear Call Credit Spread (Defined Risk)",
            entry_time_ist="09:20:00",
            square_off_time_ist="15:15:00",
            max_strategy_loss_inr=Decimal("3500.00"),
            nodes=[
                UniverseNode(node_id="u1", segment=Segment.NSE_FNO, underlying="BANKNIFTY"),
                IndicatorNode(node_id="ema20", indicator="EMA", timeframe=Timeframe.M5, params={"period": 20}),
                ActionLegNode(
                    node_id="sell_atm_ce", trigger_node_id="ema20", universe_node_id="u1", side="SELL", lots=1,
                    strike_config=OptionStrikeConfig(option_type="CE", atm_offset_steps=0),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("30.0")),
                ),
                ActionLegNode(
                    node_id="buy_otm_ce", trigger_node_id="ema20", universe_node_id="u1", side="BUY", lots=1,
                    strike_config=OptionStrikeConfig(option_type="CE", atm_offset_steps=3),
                    risk_config=RiskLegConfig(stop_loss_value=Decimal("75.0")),
                ),
            ],
            edges=[
                DAGEdge(id="e1", source="u1", target="ema20"),
                DAGEdge(id="e2", source="ema20", target="sell_atm_ce"),
                DAGEdge(id="e3", source="ema20", target="buy_otm_ce"),
            ],
        ),
    ]

    return [
        {
            "name": ast.strategy_name,
            "visibility": "WHITE_BOX_PUBLIC",
            "ast_payload": ast.model_dump(mode="json"),
            "ast_sha256_hash": ast.compute_cryptographic_hash(),
        }
        for ast in blueprints
    ]
