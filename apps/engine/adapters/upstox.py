# apps/engine/adapters/upstox.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
from apps.engine.workers.order_router import BrokerAdapter, NormalizedOrderRequest


class UpstoxV2Adapter(BrokerAdapter):
    """
    Production Upstox v2 REST Adapter.
    Enforces Static Egress IP binding, Bearer OAuth tokens, and 9-OPS rate limit.
    """
    BASE_URL = "https://api.upstox.com/v2"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        instrument_key = order.trading_symbol
        payload = {
            "quantity": slice_qty,
            "product": "I" if order.product == "MIS" else "D",
            "validity": "DAY",
            "price": float(limit_price),
            "tag": order.exchange_algo_id[:20],
            "instrument_token": instrument_key,
            "order_type": "LIMIT",
            "transaction_type": order.side,
            "disclosed_quantity": 0,
            "trigger_price": 0.0,
            "is_amo": False,
        }
        resp = await self.http.post(
            f"{self.BASE_URL}/order/place",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Upstox Order Rejected: {data.get('errors')}")
        return str(data["data"]["order_id"])

    async def cancel_all_open_orders(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/order/retrieve-all", headers=self._headers)
        resp.raise_for_status()
        orders = resp.json().get("data") or []
        cancelled_ids: List[str] = []

        for o in orders:
            if o.get("status") in ("open", "trigger pending"):
                c_resp = await self.http.delete(
                    f"{self.BASE_URL}/order/cancel?order_id={o['order_id']}",
                    headers=self._headers,
                )
                if c_resp.status_code == 200:
                    cancelled_ids.append(str(o["order_id"]))
        return cancelled_ids

    async def square_off_all_positions(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/portfolio/short-term-positions", headers=self._headers)
        resp.raise_for_status()
        positions = resp.json().get("data") or []
        squared_ids: List[str] = []

        for pos in positions:
            qty = int(pos.get("quantity", 0))
            if qty == 0:
                continue
            exit_side = "SELL" if qty > 0 else "BUY"
            ltp = Decimal(str(pos.get("last_price", "100.00")))
            mpp_price = (
                ltp * (Decimal("0.99") if exit_side == "SELL" else Decimal("1.01"))
            ).quantize(Decimal("0.05"))

            payload = {
                "quantity": abs(qty),
                "product": pos["product"],
                "validity": "DAY",
                "price": float(mpp_price),
                "tag": "KILLSWITCH",
                "instrument_token": pos["instrument_token"],
                "order_type": "LIMIT",
                "transaction_type": exit_side,
                "disclosed_quantity": 0,
                "trigger_price": 0.0,
                "is_amo": False,
            }
            sq_resp = await self.http.post(
                f"{self.BASE_URL}/order/place",
                json=payload,
                headers=self._headers,
            )
            if sq_resp.status_code == 200:
                squared_ids.append(str(sq_resp.json().get("data", {}).get("order_id")))

        return squared_ids
