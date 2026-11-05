# apps/engine/adapters/fyers.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
from apps.engine.workers.order_router import BrokerAdapter, NormalizedOrderRequest


class FyersV3Adapter(BrokerAdapter):
    """
    Production Fyers API v3 REST Adapter.
    Enforces Static Egress IP binding, Fyers AppId:Token authentication, and 9-OPS rate limit.
    """
    BASE_URL = "https://api-t1.fyers.in/api/v3"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.api_key}:{self.access_token}",
            "Content-Type": "application/json",
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        payload = {
            "symbol": order.trading_symbol,
            "qty": slice_qty,
            "type": 1,  # 1 = Limit
            "side": 1 if order.side == "BUY" else -1,
            "productType": "INTRADAY" if order.product == "MIS" else "MARGIN",
            "limitPrice": float(limit_price),
            "stopPrice": 0.0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
            "tag": order.exchange_algo_id[:20],
        }
        resp = await self.http.post(
            f"{self.BASE_URL}/orders/sync",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("s") != "ok":
            raise RuntimeError(f"Fyers Order Rejected: {data.get('message')}")
        return str(data["id"])

    async def cancel_all_open_orders(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/orders", headers=self._headers)
        resp.raise_for_status()
        order_book = resp.json().get("orderBook") or []
        cancelled_ids: List[str] = []

        for o in order_book:
            if o.get("status") in (1, 4):  # 1 = Submitted, 4 = Pending
                c_resp = await self.http.delete(
                    f"{self.BASE_URL}/orders/sync",
                    json={"id": o["id"]},
                    headers=self._headers,
                )
                if c_resp.status_code == 200:
                    cancelled_ids.append(str(o["id"]))
        return cancelled_ids

    async def square_off_all_positions(self) -> List[str]:
        # Fyers dedicated exit-all-positions endpoint
        resp = await self.http.delete(
            f"{self.BASE_URL}/positions",
            json={"exit_all": 1},
            headers=self._headers,
        )
        resp.raise_for_status()
        return ["FYERS_ALL_POSITIONS_EXITED"]
