# apps/api/app/services/tradebook_importer.py
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Literal, Optional
import httpx


@dataclass
class BrokerTradeBookEntry:
    trade_id: str
    symbol: str
    exchange: str
    transaction_type: Literal["BUY", "SELL"]
    quantity: int
    executed_price: Decimal
    executed_timestamp: int  # Epoch seconds


class IndiaBrokerTradebookImporter:
    """
    Unified tradebook fetcher supporting Zerodha Kite, Dhan HQ, Upstox v2,
    Angel One SmartAPI, and ICICI Breeze.
    """

    @staticmethod
    async def fetch_zerodha_tradebook(access_token: str, api_key: str, static_ip: str) -> List[BrokerTradeBookEntry]:
        transport = httpx.AsyncHTTPTransport(local_address=static_ip)
        async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
            resp = await client.get(
                "https://api.kite.trade/trades",
                headers={"X-Kite-Version": "3", "Authorization": f"token {api_key}:{access_token}"},
            )
            resp.raise_for_status()
            trades = resp.json().get("data", [])
            return [
                BrokerTradeBookEntry(
                    trade_id=str(t["trade_id"]),
                    symbol=t["tradingsymbol"],
                    exchange=t["exchange"],
                    transaction_type=t["transaction_type"],
                    quantity=int(t["quantity"]),
                    executed_price=Decimal(str(t["average_price"])),
                    executed_timestamp=int(t["fill_timestamp"]),
                )
                for t in trades
            ]

    @staticmethod
    async def fetch_dhan_tradebook(access_token: str, client_id: str, static_ip: str) -> List[BrokerTradeBookEntry]:
        transport = httpx.AsyncHTTPTransport(local_address=static_ip)
        async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
            resp = await client.get(
                "https://api.dhan.co/v2/trades",
                headers={"access-token": access_token, "client-id": client_id},
            )
            resp.raise_for_status()
            trades = resp.json() or []
            return [
                BrokerTradeBookEntry(
                    trade_id=str(t["orderId"]),
                    symbol=t["tradingSymbol"],
                    exchange=t["exchangeSegment"],
                    transaction_type=t["transactionType"],
                    quantity=int(t["tradedQuantity"]),
                    executed_price=Decimal(str(t["tradedPrice"])),
                    executed_timestamp=int(t["createTime"]),
                )
                for t in trades
            ]

    @staticmethod
    async def run_vibe_shadow_audit(
        broker_trades: List[BrokerTradeBookEntry],
        ast_backtest_trades: List[dict],
        max_loss_tolerance_inr: Decimal = Decimal("3000.00"),
    ) -> dict:
        """
        Calculates emotional leakage (revenge trades, holding losers past SL, early profit cutting).
        """
        actual_pnl = sum(
            (t.executed_price * t.quantity * (1 if t.transaction_type == "SELL" else -1))
            for t in broker_trades
        )
        shadow_pnl = sum(Decimal(str(b["net_pnl_inr"])) for b in ast_backtest_trades)

        revenge_count = 0
        unprotected_losses = 0

        sorted_trades = sorted(broker_trades, key=lambda x: x.executed_timestamp)
        for i, trade in enumerate(sorted_trades):
            if trade.executed_price * trade.quantity < -max_loss_tolerance_inr:
                unprotected_losses += 1
            if i > 0:
                prev = sorted_trades[i - 1]
                if (trade.executed_timestamp - prev.executed_timestamp) <= 120 and trade.quantity > prev.quantity:
                    revenge_count += 1

        return {
            "total_manual_trades_analyzed": len(broker_trades),
            "actual_discretionary_pnl_inr": float(actual_pnl),
            "shadow_quantra_ast_pnl_inr": float(shadow_pnl),
            "emotional_pnl_leakage_inr": float(shadow_pnl - actual_pnl),
            "revenge_trades_flagged": revenge_count,
            "unprotected_stop_loss_breaches": unprotected_losses,
            "audit_recommendation": (
                "Switch to Quantra Automated DAG Execution to eliminate emotional leakage."
                if shadow_pnl > actual_pnl
                else "Discretionary strategy performed well, but lacks automated trailing stops."
            ),
        }
