# tests/test_ai_vibe_engine.py
import sys
import os
sys.path.insert(0, os.path.abspath("."))

import json
from decimal import Decimal
from apps.api.app.services.ai_vibe_engine import (
    ManualTradeRecord,
    QuantraShadowAccountAuditor,
    validate_llm_generated_ast,
    PreMarketCommitteeReport,
    AgentArgument,
)


def test_shadow_account_emotional_leakage():
    print("[+] Running Shadow Account Emotional Leakage Audit...")
    
    # 3 manual trades with revenge trading and blown SL
    manual_trades = [
        # Trade 1: Normal loss
        ManualTradeRecord(
            symbol="NIFTY24MAR22400CE", entry_ts=1710000000, exit_ts=1710000300,
            side="BUY", quantity=75, actual_entry_price=Decimal("120.0"),
            actual_exit_price=Decimal("100.0"), actual_net_pnl_inr=Decimal("-1500.00")
        ),
        # Trade 2: Revenge trade! Re-entered 60s later with double size (150 qty) and lost heavily
        ManualTradeRecord(
            symbol="NIFTY24MAR22400CE", entry_ts=1710000360, exit_ts=1710000800,
            side="BUY", quantity=150, actual_entry_price=Decimal("105.0"),
            actual_exit_price=Decimal("80.0"), actual_net_pnl_inr=Decimal("-3750.00") # Exceeds 2500 max loss!
        ),
        # Trade 3: Small emotional gain
        ManualTradeRecord(
            symbol="NIFTY24MAR22400PE", entry_ts=1710001000, exit_ts=1710001200,
            side="BUY", quantity=75, actual_entry_price=Decimal("90.0"),
            actual_exit_price=Decimal("100.0"), actual_net_pnl_inr=Decimal("750.00")
        )
    ]

    # Disciplined algo backtest had only 1 clean trade
    shadow_algo_trades = [
        {"net_pnl_inr": 2400.00}
    ]

    report = QuantraShadowAccountAuditor.audit_manual_journal_vs_ast(
        manual_trades=manual_trades,
        shadow_backtest_trades=shadow_algo_trades,
        max_allowed_loss_per_trade_inr=Decimal("2500.00")
    )

    assert report.total_manual_trades == 3
    assert report.actual_manual_net_pnl_inr == Decimal("-4500.00")
    assert report.shadow_algo_net_pnl_inr == Decimal("2400.00")
    # Emotional leakage = 2400 - (-4500) = +6900 INR
    assert report.emotional_leakage_inr == Decimal("6900.00")
    assert report.revenge_trades_detected == 1
    assert report.unprotected_no_sl_trades == 1

    print(f"  [OK] Emotional Leakage audited: INR {report.emotional_leakage_inr} lost to {report.revenge_trades_detected} revenge trades.")


def test_vibe_to_ast_validation():
    print("[+] Testing Vibe-to-AST Pydantic v2 Validator...")
    sample_json = json.dumps({
        "schema_version": "2.0.0",
        "strategy_name": "Vibe Short Straddle",
        "entry_time_ist": "09:20:00",
        "square_off_time_ist": "15:10:00",
        "max_strategy_loss_inr": "5000.00",
        "nodes": [
            {"node_id": "u1", "node_type": "UNIVERSE", "segment": "NSE_FNO", "underlying": "NIFTY", "expiry_type": "WEEKLY_CURRENT"},
            {"node_id": "i1", "node_type": "INDICATOR", "indicator": "RSI", "timeframe": "5m", "params": {"period": 14}, "candle_offset": 0},
            {"node_id": "leg1", "node_type": "ACTION_LEG", "trigger_node_id": "i1", "universe_node_id": "u1", "side": "SELL", "lots": 2,
             "strike_config": {"option_type": "CE", "selection_mode": "ATM_OFFSET", "atm_offset_steps": 0},
             "risk_config": {"stop_loss_type": "PERCENT", "stop_loss_value": "20.0", "target_type": "NONE", "trailing_sl_enabled": False, "move_sl_to_cost_on_other_leg_sl": True, "max_reentries_on_sl": 0},
             "mpp_slippage_bps": 50}
        ],
        "edges": [
            {"id": "e1", "source": "u1", "target": "i1"},
            {"id": "e2", "source": "i1", "target": "leg1"}
        ]
    })

    ast = validate_llm_generated_ast(sample_json)
    assert ast.strategy_name == "Vibe Short Straddle"
    assert len(ast.nodes) == 3
    print("  [OK] Vibe LLM JSON correctly validated into StrategyAST with cryptographic hash: " + ast.compute_cryptographic_hash()[:16] + "...")


if __name__ == "__main__":
    test_shadow_account_emotional_leakage()
    test_vibe_to_ast_validation()
    print("ALL AI COPILOT & VIBE-TRADING TESTS PASSED!")
