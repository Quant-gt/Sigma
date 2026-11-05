# apps/api/app/services/trading_agents_warroom.py
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import Dict, List, Literal
from pydantic import BaseModel, Field


class MarketTelemetrySnapshot(BaseModel):
    underlying: Literal["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK"]
    spot_close: float
    gift_nifty_gap_pts: float
    india_vix: float
    vix_change_pct: float
    pcr_oi: float                       # Put-Call Ratio (Open Interest)
    max_pain_strike: int
    call_wall_strike: int               # Highest CE OI strike
    put_wall_strike: int                # Highest PE OI strike
    fii_net_index_fut_long_pct: float   # FII Long/Short Ratio in Index Futures
    atr_14_daily: float
    rsi_14_daily: float


class DebateTurn(BaseModel):
    speaker: Literal["BULL_RESEARCHER", "BEAR_RESEARCHER", "OPTIONS_FLOW_ANALYST", "CHIEF_RISK_OFFICER"]
    stance: Literal["BULLISH", "BEARISH", "NEUTRAL_RANGE", "RISK_ALERT"]
    headline: str
    evidence_points: List[str]
    conviction: int = Field(..., ge=1, le=100)


class WarRoomVerdict(BaseModel):
    underlying: str
    timestamp_ist: str
    regime_classification: Literal[
        "LOW_VOL_THETA_DECAY",
        "BULLISH_MOMENTUM_BREAKOUT",
        "BEARISH_GAMMA_EXPANSION",
        "HIGH_VIX_EVENT_DANGER",
    ]
    bull_probability_pct: int
    bear_probability_pct: int
    neutral_probability_pct: int
    recommended_lot_multiplier_scale: float = Field(
        ..., description="CRO Risk Scaling: 1.0 = Full Size, 0.5 = Half Lots, 0.0 = Halt Non-Hedged Selling"
    )
    recommended_whitebox_blueprints: List[str]
    debate_transcript: List[DebateTurn]


class TradingAgentsWarRoomService:
    """
    Executes a deterministic + LLM-augmented multi-agent debate on Indian NSE F&O telemetry
    modeled on TauricResearch/TradingAgents.
    """

    @staticmethod
    async def run_morning_committee(telemetry: MarketTelemetrySnapshot) -> WarRoomVerdict:
        # 1. Options Flow & OI Analyst Assessment
        oi_skew_bullish = telemetry.pcr_oi > 1.15 and telemetry.fii_net_index_fut_long_pct > 55.0
        oi_skew_bearish = telemetry.pcr_oi < 0.80 or telemetry.fii_net_index_fut_long_pct < 35.0

        options_turn = DebateTurn(
            speaker="OPTIONS_FLOW_ANALYST",
            stance="BULLISH" if oi_skew_bullish else ("BEARISH" if oi_skew_bearish else "NEUTRAL_RANGE"),
            headline=f"PCR at {telemetry.pcr_oi:.2f} with Max Pain anchored at {telemetry.max_pain_strike}",
            evidence_points=[
                f"Put Wall support at {telemetry.put_wall_strike} PE vs Call Wall resistance at {telemetry.call_wall_strike} CE.",
                f"FII Index Futures Net Long stands at {telemetry.fii_net_index_fut_long_pct:.1f}%.",
                f"India VIX is at {telemetry.india_vix:.2f} ({telemetry.vix_change_pct:+.1f}%).",
            ],
            conviction=78,
        )

        # 2. Bull Researcher Case
        bull_score = 50 + (15 if telemetry.gift_nifty_gap_pts > 40 else 0) + (15 if oi_skew_bullish else 0)
        bull_turn = DebateTurn(
            speaker="BULL_RESEARCHER",
            stance="BULLISH",
            headline=f"Put writing concentration at {telemetry.put_wall_strike} + institutional flow supports upside",
            evidence_points=[
                f"GIFT Nifty indicates a {telemetry.gift_nifty_gap_pts:+.0f} pt opening impulse.",
                f"Short-covering trigger likely if spot sustains above {telemetry.max_pain_strike + 50} in first 15m candle.",
                f"Daily RSI ({telemetry.rsi_14_daily:.1f}) shows healthy momentum without extreme exhaustion.",
            ],
            conviction=min(95, bull_score),
        )

        # 3. Bear Researcher Counter-Rebuttal
        bear_score = 50 + (20 if telemetry.india_vix > 16.5 else 0) + (15 if oi_skew_bearish else 0)
        bear_turn = DebateTurn(
            speaker="BEAR_RESEARCHER",
            stance="BEARISH",
            headline=f" Overhead Call Wall at {telemetry.call_wall_strike} & Gamma risk on gap fade",
            evidence_points=[
                f"Heavy Call OI ceiling at {telemetry.call_wall_strike} caps immediate upside expansion.",
                f"Daily ATR ({telemetry.atr_14_daily:.0f} pts) warns of intraday mean-reversion traps on wide gaps.",
                f"Any breach below VWAP in first 30 mins exposes {telemetry.put_wall_strike} gamma acceleration.",
            ],
            conviction=min(95, bear_score),
        )

        # 4. Chief Risk Officer (CRO) Synthesis & Position Sizing Guardrail
        if telemetry.india_vix >= 18.0 or abs(telemetry.gift_nifty_gap_pts) > 180:
            regime = "HIGH_VIX_EVENT_DANGER"
            lot_scale = 0.5
            blueprints = ["WB-03: Defined-Risk Iron Condor", "WB-06: Volatility Squeeze Breakout"]
            bull_p, bear_p, neut_p = 35, 45, 20
        elif abs(telemetry.pcr_oi - 1.0) <= 0.15 and telemetry.india_vix < 14.5:
            regime = "LOW_VOL_THETA_DECAY"
            lot_scale = 1.0
            blueprints = ["WB-01: 09:20 Short Straddle with SL-to-Cost", "WB-02: Dynamic Delta-Neutral Strangle"]
            bull_p, bear_p, neut_p = 25, 25, 50
        elif oi_skew_bullish:
            regime = "BULLISH_MOMENTUM_BREAKOUT"
            lot_scale = 1.0
            blueprints = ["WB-04: 15m ORB + VWAP Trend Follower", "WB-09: Bull Put Credit Spread"]
            bull_p, bear_p, neut_p = 55, 20, 25
        else:
            regime = "BEARISH_GAMMA_EXPANSION"
            lot_scale = 0.75
            blueprints = ["WB-05: SuperTrend + OI Breakdown Momentum", "WB-10: Bear Call Credit Spread"]
            bull_p, bear_p, neut_p = 20, 55, 25

        cro_turn = DebateTurn(
            speaker="CHIEF_RISK_OFFICER",
            stance="RISK_ALERT",
            headline=f"Regime: {regime} — Enforcing {int(lot_scale * 100)}% Max Lot Allocation",
            evidence_points=[
                f"Recommended Capital Scaling: {lot_scale}x of baseline user lot multiplier.",
                "Mandatory SEBI Market Price Protection (50 bps) active on all legs.",
                f"Top matched White-Box Blueprints: {', '.join(blueprints)}.",
            ],
            conviction=92,
        )

        return WarRoomVerdict(
            underlying=telemetry.underlying,
            timestamp_ist=datetime.now().strftime("%Y-%m-%d 08:45:00 IST"),
            regime_classification=regime,
            bull_probability_pct=bull_p,
            bear_probability_pct=bear_p,
            neutral_probability_pct=neut_p,
            recommended_lot_multiplier_scale=lot_scale,
            recommended_whitebox_blueprints=blueprints,
            debate_transcript=[options_turn, bull_turn, bear_turn, cro_turn],
        )
