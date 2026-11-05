# apps/api/app/services/ai_vibe_engine.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Literal
from pydantic import BaseModel, Field

from apps.api.app.schemas.ast_schema import StrategyAST


# ============================================================================
# 1. TRADINGAGENTS MULTI-AGENT DEBATE OUTPUT SCHEMA (EXPLAINABLE AI BRIEF)
# ============================================================================
class AgentArgument(BaseModel):
    agent_role: Literal[
        "FUNDAMENTAL_ANALYST",
        "TECHNICAL_ANALYST",
        "OPTIONS_FLOW_ANALYST",
        "BULL_RESEARCHER",
        "BEAR_RESEARCHER",
        "RISK_MANAGER",
    ]
    key_thesis: str
    supporting_metrics: List[str]
    confidence_score: float = Field(..., ge=0.0, le=1.0)


class PreMarketCommitteeReport(BaseModel):
    """
    Structured output modeled on TauricResearch/TradingAgents v0.6.0.
    Used strictly as an explainable pre-market regime brief — never fires raw unvalidated orders.
    """
    underlying: str = Field(..., examples=["NIFTY", "BANKNIFTY", "RELIANCE.NS"])
    analysis_date: str
    market_regime: Literal["TRENDING_BULL", "TRENDING_BEAR", "MEAN_REVERTING_RANGE", "HIGH_IV_EVENT_RISK"]
    recommended_strategy_archetype: Literal[
        "SHORT_STRADDLE_STRANGLE",
        "DIRECTIONAL_MOMENTUM_BREAKOUT",
        "IRON_CONDOR_DEFINED_RISK",
        "STAY_IN_CASH_HIGH_RISK",
    ]
    committee_debate_log: List[AgentArgument]
    risk_manager_max_lot_scaling: float = Field(
        ..., ge=0.0, le=1.0, description="0.0 = Halt trading on high event risk, 1.0 = Full normal size"
    )


# ============================================================================
# 2. VIBE-TRADING "SHADOW ACCOUNT" REPLAY ENGINE (MANUAL VS ALGO AUDIT)
# ============================================================================
class ManualTradeRecord(BaseModel):
    symbol: str
    entry_ts: int
    exit_ts: int
    side: Literal["BUY", "SELL"]
    quantity: int
    actual_entry_price: Decimal
    actual_exit_price: Decimal
    actual_net_pnl_inr: Decimal


class ShadowComparisonReport(BaseModel):
    total_manual_trades: int
    actual_manual_net_pnl_inr: Decimal
    shadow_algo_net_pnl_inr: Decimal
    emotional_leakage_inr: Decimal  # How much money the trader lost by breaking rules
    revenge_trades_detected: int
    early_profit_exits_detected: int
    unprotected_no_sl_trades: int


class QuantraShadowAccountAuditor:
    """
    Inspired by HKUDS/Vibe-Trading `/shadow` command:
    Imports a trader's actual Zerodha/Dhan/ICICI tradebook and compares their emotional
    execution against what a disciplined Quantra StrategyAST would have returned.
    """

    @staticmethod
    def audit_manual_journal_vs_ast(
        manual_trades: List[ManualTradeRecord],
        shadow_backtest_trades: List[Dict],
        max_allowed_loss_per_trade_inr: Decimal = Decimal("2500.00"),
    ) -> ShadowComparisonReport:
        actual_pnl = sum((t.actual_net_pnl_inr for t in manual_trades), Decimal("0.00"))
        shadow_pnl = sum(
            (Decimal(str(t["net_pnl_inr"])) for t in shadow_backtest_trades),
            Decimal("0.00"),
        )

        revenge_count = 0
        unprotected_sl_count = 0

        sorted_manual = sorted(manual_trades, key=lambda x: x.entry_ts)
        for i, trade in enumerate(sorted_manual):
            # Detect blown stop-loss (emotional holding of losers)
            if trade.actual_net_pnl_inr < -max_allowed_loss_per_trade_inr:
                unprotected_sl_count += 1

            # Detect revenge trade (re-entering within 180 seconds after a losing trade with larger size)
            if i > 0:
                prev = sorted_manual[i - 1]
                if (
                    prev.actual_net_pnl_inr < 0
                    and (trade.entry_ts - prev.exit_ts) <= 180
                    and trade.quantity > prev.quantity
                ):
                    revenge_count += 1

        return ShadowComparisonReport(
            total_manual_trades=len(manual_trades),
            actual_manual_net_pnl_inr=actual_pnl,
            shadow_algo_net_pnl_inr=shadow_pnl,
            emotional_leakage_inr=shadow_pnl - actual_pnl,
            revenge_trades_detected=revenge_count,
            early_profit_exits_detected=max(0, len(manual_trades) - len(shadow_backtest_trades)),
            unprotected_no_sl_trades=unprotected_sl_count,
        )


# ============================================================================
# 3. VIBE-TRADING NATURAL LANGUAGE -> QUANTRA DAG AST COMPILER
# ============================================================================
VIBE_TO_AST_SYSTEM_PROMPT = """
You are the Quantra Vibe-to-AST Compiler.
Convert the user's natural language trading idea into a strictly valid Quantra `StrategyAST` JSON object.
RULES:
1. Never output Python code or prose. Output ONLY JSON conforming to `StrategyAST` schema_version '2.0.0'.
2. Every graph MUST be a strict Directed Acyclic Graph (DAG) starting with a `UNIVERSE` node, flowing through `INDICATOR` / `COMPARISON` / `LOGIC_GATE` nodes, and terminating in at least one `ACTION_LEG` node.
3. All F&O legs MUST include an explicit `risk_config` with a positive `stop_loss_value` and `mpp_slippage_bps` between 5 and 300 to satisfy SEBI compliance.
"""


def validate_llm_generated_ast(raw_llm_json: str) -> StrategyAST:
    """
    Parses LLM JSON output from Vibe-Trading prompt and runs full Pydantic v2 + Kahn's
    cycle detection before allowing it onto the React Flow canvas.
    """
    return StrategyAST.model_validate_json(raw_llm_json)
