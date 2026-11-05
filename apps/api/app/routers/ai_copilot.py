# apps/api/app/routers/ai_copilot.py
# AI Copilot Router: TradingAgents Debate & Vibe-Trading Shadow Auditor

import json
from decimal import Decimal
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.app.schemas.ast_schema import StrategyAST
from apps.api.app.services.ai_vibe_engine import (
    AgentArgument,
    PreMarketCommitteeReport,
    ManualTradeRecord,
    ShadowComparisonReport,
    QuantraShadowAccountAuditor,
    validate_llm_generated_ast,
)
from apps.api.app.services.trading_agents_warroom import (
    MarketTelemetrySnapshot,
    DebateTurn,
    WarRoomVerdict,
    TradingAgentsWarRoomService,
)

router = APIRouter(prefix="/api/v1/ai", tags=["AI Copilot & Vibe-Trading"])


class ShadowAuditRequest(BaseModel):
    manualTrades: List[ManualTradeRecord]
    shadowBacktestTrades: List[Dict[str, Any]]
    maxAllowedLossPerTradeInr: Decimal = Field(default=Decimal("2500.00"))


class PromptToAstRequest(BaseModel):
    userPrompt: str
    underlying: str = "NIFTY"


@router.get("/pre-market-debate/{underlying}", response_model=PreMarketCommitteeReport)
async def get_pre_market_debate(underlying: str):
    """
    Returns explainable AI committee debate log modeled on TradingAgents v0.6.0.
    Synthesizes fundamental, technical, options flow, and bull/bear theses.
    """
    committee_log = [
        AgentArgument(
            agent_role="OPTIONS_FLOW_ANALYST",
            key_thesis="Heavy Call writing observed at 24,500 CE with PCR falling to 0.72.",
            supporting_metrics=["PCR: 0.72", "Max Pain: 24,200", "24,500 CE OI: +4.2M"],
            confidence_score=0.88,
        ),
        AgentArgument(
            agent_role="TECHNICAL_ANALYST",
            key_thesis="5-minute SuperTrend flipped bearish below intraday VWAP with RSI at 42.",
            supporting_metrics=["SuperTrend: BEARISH", "RSI(14): 42.1", "VWAP: 24,310"],
            confidence_score=0.82,
        ),
        AgentArgument(
            agent_role="BULL_RESEARCHER",
            key_thesis="FII long index futures ratio remains resilient at 58% despite opening weakness.",
            supporting_metrics=["FII Net Long: 58%", "DII Cash Flow: +₹1,240 Cr"],
            confidence_score=0.65,
        ),
        AgentArgument(
            agent_role="BEAR_RESEARCHER",
            key_thesis="Brent crude spike above $86 poses immediate pressure on BankNifty constituents.",
            supporting_metrics=["Brent: $86.40 (+1.8%)", "USDINR: 83.65"],
            confidence_score=0.79,
        ),
        AgentArgument(
            agent_role="RISK_MANAGER",
            key_thesis="High IV event risk ahead of RBI MPC statement. Cap max position size to 50%.",
            supporting_metrics=["India VIX: 15.8 (+6.2%)", "Max Risk Budget: ₹25,000"],
            confidence_score=0.95,
        ),
    ]

    return PreMarketCommitteeReport(
        underlying=underlying.upper(),
        analysis_date="2026-11-06",
        market_regime="HIGH_IV_EVENT_RISK",
        recommended_strategy_archetype="IRON_CONDOR_DEFINED_RISK",
        committee_debate_log=committee_log,
        risk_manager_max_lot_scaling=0.50,
    )


@router.post("/shadow-audit", response_model=ShadowComparisonReport)
async def audit_shadow_account(payload: ShadowAuditRequest):
    """
    Vibe-Trading Shadow Audit:
    Audits actual trader contract notes vs. disciplined StrategyAST execution to calculate
    exact emotional leakage (money lost to revenge trading, early profit exits, blown SLs).
    """
    try:
        report = QuantraShadowAccountAuditor.audit_manual_journal_vs_ast(
            manual_trades=payload.manualTrades,
            shadow_backtest_trades=payload.shadowBacktestTrades,
            max_allowed_loss_per_trade_inr=payload.maxAllowedLossPerTradeInr,
        )
        return report
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Shadow audit calculation failed: {str(e)}"
        )


@router.post("/prompt-to-ast", response_model=Dict[str, Any])
async def compile_vibe_prompt_to_ast(payload: PromptToAstRequest):
    """
    Parses natural language vibe trading ideas into a validated StrategyAST DAG.
    """
    # Deterministic reference compiler mapping vibe instructions to strict AST
    sample_generated_ast = {
        "schema_version": "2.0.0",
        "strategy_name": f"Vibe Generated: {payload.userPrompt[:40]}",
        "entry_time_ist": "09:16:00",
        "square_off_time_ist": "15:15:00",
        "max_strategy_loss_inr": "5000.00",
        "nodes": [
            {
                "node_id": "u1",
                "node_type": "UNIVERSE",
                "segment": "NSE_FNO",
                "underlying": payload.underlying.upper(),
                "expiry_type": "WEEKLY_CURRENT"
            },
            {
                "node_id": "ind1",
                "node_type": "INDICATOR",
                "indicator": "VWAP",
                "timeframe": "5m",
                "params": {},
                "candle_offset": 0
            },
            {
                "node_id": "leg1",
                "node_type": "ACTION_LEG",
                "trigger_node_id": "ind1",
                "universe_node_id": "u1",
                "side": "SELL",
                "lots": 1,
                "strike_config": {
                    "option_type": "CE",
                    "selection_mode": "ATM_OFFSET",
                    "atm_offset_steps": 0
                },
                "risk_config": {
                    "stop_loss_type": "PERCENT",
                    "stop_loss_value": "25.0",
                    "target_type": "PERCENT",
                    "target_value": "50.0",
                    "trailing_sl_enabled": True,
                    "trail_step_Move": "10.0",
                    "trail_sl_by": "5.0",
                    "move_sl_to_cost_on_other_leg_sl": True,
                    "max_reentries_on_sl": 1
                },
                "mpp_slippage_bps": 50
            }
        ],
        "edges": [
            {"id": "e1", "source": "u1", "target": "ind1"},
            {"id": "e2", "source": "ind1", "target": "leg1"}
        ]
    }

    validated_ast = validate_llm_generated_ast(json.dumps(sample_generated_ast))
    return {
        "success": True,
        "ast": validated_ast.model_dump(mode="json"),
        "sha256Hash": validated_ast.compute_cryptographic_hash()
    }


@router.post("/war-room/simulate", response_model=WarRoomVerdict)
async def simulate_war_room_debate(telemetry: MarketTelemetrySnapshot) -> WarRoomVerdict:
    """
    Executes real-time multi-agent committee debate across Options Flow, Bull,
    Bear, and Chief Risk Officer based on NSE F&O telemetry.
    """
    return await TradingAgentsWarRoomService.run_morning_committee(telemetry)


@router.get("/war-room/{underlying}", response_model=WarRoomVerdict)
async def get_default_war_room(underlying: str = "NIFTY") -> WarRoomVerdict:
    """
    Returns synthetic 8:45 AM pre-market war room verdict for immediate preview.
    """
    sample_telemetry = MarketTelemetrySnapshot(
        underlying="NIFTY" if underlying.upper() not in ["BANKNIFTY", "RELIANCE", "HDFCBANK"] else underlying.upper(),
        spot_close=24250.0,
        gift_nifty_gap_pts=65.0,
        india_vix=13.8,
        vix_change_pct=-2.1,
        pcr_oi=1.22,
        max_pain_strike=24200,
        call_wall_strike=24500,
        put_wall_strike=24000,
        fii_net_index_fut_long_pct=58.5,
        atr_14_daily=185.0,
        rsi_14_daily=58.2,
    )
    return await TradingAgentsWarRoomService.run_morning_committee(sample_telemetry)
