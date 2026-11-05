# tests/test_tradebook_importer.py
import sys
import os
import asyncio
from decimal import Decimal

sys.path.insert(0, os.path.abspath("."))

from apps.api.app.services.tradebook_importer import (
    BrokerTradeBookEntry,
    IndiaBrokerTradebookImporter,
)


def test_tradebook_shadow_audit():
    print("[+] Testing IndiaBrokerTradebookImporter Vibe Shadow Audit...")

    # Simulated manual trades: 1 normal loss, 1 revenge trade 60s later with double qty, 1 win
    manual_trades = [
        BrokerTradeBookEntry(
            trade_id="T1", symbol="NIFTY24MAR22400CE", exchange="NSE",
            transaction_type="BUY", quantity=75, executed_price=Decimal("120.0"),
            executed_timestamp=1710000000
        ),
        BrokerTradeBookEntry(
            trade_id="T2", symbol="NIFTY24MAR22400CE", exchange="NSE",
            transaction_type="SELL", quantity=75, executed_price=Decimal("100.0"),
            executed_timestamp=1710000300
        ),
        # Revenge trade: re-entered 60s later with double quantity (150) and took large loss
        BrokerTradeBookEntry(
            trade_id="T3", symbol="NIFTY24MAR22400CE", exchange="NSE",
            transaction_type="BUY", quantity=150, executed_price=Decimal("110.0"),
            executed_timestamp=1710000360
        ),
        BrokerTradeBookEntry(
            trade_id="T4", symbol="NIFTY24MAR22400CE", exchange="NSE",
            transaction_type="SELL", quantity=150, executed_price=Decimal("80.0"),
            executed_timestamp=1710000800
        ),
    ]

    # Disciplined Quantra Strategy AST backtest results for same session
    ast_backtest = [
        {"net_pnl_inr": 2800.00}
    ]

    report = asyncio.run(
        IndiaBrokerTradebookImporter.run_vibe_shadow_audit(
            broker_trades=manual_trades,
            ast_backtest_trades=ast_backtest,
            max_loss_tolerance_inr=Decimal("2500.00")
        )
    )

    assert report["total_manual_trades_analyzed"] == 4
    assert report["revenge_trades_flagged"] == 1
    assert report["shadow_quantra_ast_pnl_inr"] == 2800.0
    assert report["emotional_pnl_leakage_inr"] > 0
    print("  [OK] Revenge trade flagged: 1")
    print(f"  [OK] Shadow Quantra AST PnL: INR {report['shadow_quantra_ast_pnl_inr']}")
    print(f"  [OK] Emotional Leakage computed: INR {report['emotional_pnl_leakage_inr']}")

    print("ALL TRADEBOOK IMPORTER TESTS PASSED!")


if __name__ == "__main__":
    test_tradebook_shadow_audit()
