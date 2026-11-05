# apps/engine/adapters/angelone.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List
from apps.engine.workers.order_router import BrokerAdapter, NormalizedOrderRequest


class AngelOneSmartAPIAdapter(BrokerAdapter):
    """
    Production Angel One SmartAPI REST Adapter.
    Enforces Static Egress IP binding, JWT auth, and SEBI Algo ID tagging.
    """
    BASE_URL = "https://apiconnect.angelone.in"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": self.static_egress_ip,
            "X-ClientPublicIP": self.static_egress_ip,
            "X-PrivateKey": self.api_key,
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        exchange_seg = "NFO" if order.exchange in ("NFO", "BFO") else "NSE"
        payload = {
            "variety": "NORMAL",
            "tradingsymbol": order.trading_symbol,
            "symboltoken": order.trading_symbol,
            "transactiontype": order.side,
            "exchange": exchange_seg,
            "ordertype": "LIMIT",
            "producttype": "INTRADAY" if order.product == "MIS" else "CARRYFORWARD",
            "duration": "DAY",
            "price": str(limit_price),
            "quantity": str(slice_qty),
            "ordertag": order.exchange_algo_id[:20],
        }
        resp = await self.http.post(
            f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/placeOrder",
            json=payload,
            headers=self._headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("status") or not data.get("data"):
            raise RuntimeError(f"Angel One Order Rejected: {data.get('message')}")
        return str(data["data"]["orderid"])

    async def cancel_all_open_orders(self) -> List[str]:
        resp = await self.http.get(
            f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getOrderBook",
            headers=self._headers,
        )
        resp.raise_for_status()
        orders = resp.json().get("data") or []
        cancelled_ids: List[str] = []

        for o in orders:
            if o.get("orderstatus") in ("open", "trigger pending"):
                cancel_payload = {
                    "variety": "NORMAL",
                    "orderid": o["orderid"],
                }
                c_resp = await self.http.post(
                    f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/cancelOrder",
                    json=cancel_payload,
                    headers=self._headers,
                )
                if c_resp.status_code == 200:
                    cancelled_ids.append(str(o["orderid"]))
        return cancelled_ids

    async def square_off_all_positions(self) -> List[str]:
        resp = await self.http.get(
            f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/getPosition",
            headers=self._headers,
        )
        resp.raise_for_status()
        positions = resp.json().get("data") or []
        squared_ids: List[str] = []

        for pos in positions:
            qty = int(pos.get("netqty", 0))
            if qty == 0:
                continue
            exit_side = "SELL" if qty > 0 else "BUY"
            ltp = Decimal(str(pos.get("ltp", "100.00")))
            mpp_price = (
                ltp * (Decimal("0.99") if exit_side == "SELL" else Decimal("1.01"))
            ).quantize(Decimal("0.05"))

            sq_payload = {
                "variety": "NORMAL",
                "tradingsymbol": pos["tradingsymbol"],
                "symboltoken": pos["symboltoken"],
                "transactiontype": exit_side,
                "exchange": pos["exchange"],
                "ordertype": "LIMIT",
                "producttype": pos["producttype"],
                "duration": "DAY",
                "price": str(mpp_price),
                "quantity": str(abs(qty)),
                "ordertag": "KILLSWITCH",
            }
            sq_resp = await self.http.post(
                f"{self.BASE_URL}/rest/secure/angelbroking/order/v1/placeOrder",
                json=sq_payload,
                headers=self._headers,
            )
            if sq_resp.status_code == 200 and sq_resp.json().get("status"):
                squared_ids.append(str(sq_resp.json()["data"]["orderid"]))

        return squared_ids
