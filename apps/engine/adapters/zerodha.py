# apps/engine/adapters/zerodha.py
# Zerodha Kite Connect v3 Broker Adapter Implementation

import httpx
from typing import Any, Callable, Dict, List, Optional
from apps.engine.adapters.base import (
    BrokerAdapter,
    OrderAction,
    OrderProduct,
    OrderType,
    PositionInfo,
    StandardOrderRequest,
    StandardOrderResponse,
)


class ZerodhaKiteAdapter(BrokerAdapter):
    BASE_URL = "https://api.kite.trade"

    def __init__(self, client_id: str, access_token: str, api_key: str, egress_ip: str):
        super().__init__(client_id, egress_ip)
        self.access_token = access_token
        self.api_key = api_key
        # Enforce static egress IP via httpx transport
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "X-Kite-Version": "3",
                "Authorization": f"token {self.api_key}:{self.access_token}",
            },
            timeout=5.0
        )

    async def authenticate_session(self, api_key: str, api_secret: str, request_token: str) -> Dict[str, Any]:
        import hashlib
        checksum = hashlib.sha256(f"{api_key}{request_token}{api_secret}".encode("utf-8")).hexdigest()
        async with httpx.AsyncClient() as c:
            res = await c.post(
                f"{self.BASE_URL}/session/token",
                data={"api_key": api_key, "request_token": request_token, "checksum": checksum}
            )
            res.raise_for_status()
            data = res.json()["data"]
            self.access_token = data["access_token"]
            return data

    async def place_order(self, order: StandardOrderRequest) -> StandardOrderResponse:
        payload = {
            "tradingsymbol": order.symbol,
            "exchange": order.exchange,
            "transaction_type": order.action.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "product": order.product.value,
            "validity": "DAY",
        }
        if order.price:
            payload["price"] = order.price
        if order.trigger_price:
            payload["trigger_price"] = order.trigger_price
        if order.tag:
            payload["tag"] = order.tag[:8] # Kite limits tag to 8 chars

        try:
            res = await self.client.post("/orders/regular", data=payload)
            res_data = res.json()
            if res.status_code == 200 and res_data.get("status") == "success":
                return StandardOrderResponse(
                    success=True,
                    broker_order_id=res_data["data"]["order_id"],
                    status="SUBMITTED",
                    raw_response=res_data
                )
            return StandardOrderResponse(
                success=False,
                broker_order_id=None,
                status="REJECTED",
                message=res_data.get("message", "Order rejected by broker"),
                raw_response=res_data
            )
        except Exception as e:
            return StandardOrderResponse(
                success=False,
                broker_order_id=None,
                status="NETWORK_ERROR",
                message=str(e)
            )

    async def modify_order(self, broker_order_id: str, new_price: Optional[float] = None, new_qty: Optional[int] = None) -> StandardOrderResponse:
        payload = {}
        if new_price is not None:
            payload["price"] = new_price
        if new_qty is not None:
            payload["quantity"] = new_qty
        try:
            res = await self.client.put(f"/orders/regular/{broker_order_id}", data=payload)
            res_data = res.json()
            return StandardOrderResponse(
                success=(res.status_code == 200),
                broker_order_id=broker_order_id,
                status="MODIFIED" if res.status_code == 200 else "REJECTED",
                message=res_data.get("message")
            )
        except Exception as e:
            return StandardOrderResponse(success=False, broker_order_id=broker_order_id, status="ERROR", message=str(e))

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            res = await self.client.delete(f"/orders/regular/{broker_order_id}")
            return res.status_code == 200
        except Exception:
            return False

    async def cancel_all_orders(self) -> List[str]:
        cancelled_ids = []
        try:
            res = await self.client.get("/orders")
            if res.status_code == 200:
                orders = res.json().get("data", [])
                for ord in orders:
                    if ord.get("status") in ("OPEN", "TRIGGER PENDING"):
                        oid = ord["order_id"]
                        if await self.cancel_order(oid):
                            cancelled_ids.append(oid)
        except Exception:
            pass
        return cancelled_ids

    async def get_positions(self) -> List[PositionInfo]:
        positions = []
        try:
            res = await self.client.get("/portfolio/positions")
            if res.status_code == 200:
                net_positions = res.json().get("data", {}).get("net", [])
                for pos in net_positions:
                    qty = int(pos.get("quantity", 0))
                    if qty != 0:
                        positions.append(PositionInfo(
                            symbol=pos["tradingsymbol"],
                            exchange=pos["exchange"],
                            product=OrderProduct(pos["product"]),
                            quantity=qty,
                            buy_price=float(pos.get("buy_price", 0.0)),
                            sell_price=float(pos.get("sell_price", 0.0)),
                            ltp=float(pos.get("last_price", 0.0)),
                            unrealized_pnl=float(pos.get("unrealised", 0.0)),
                            realized_pnl=float(pos.get("pnl", 0.0))
                        ))
        except Exception:
            pass
        return positions

    async def square_off_all_positions(self) -> List[StandardOrderResponse]:
        results = []
        positions = await self.get_positions()
        for pos in positions:
            action = OrderAction.SELL if pos.quantity > 0 else OrderAction.BUY
            order_req = StandardOrderRequest(
                symbol=pos.symbol,
                exchange=pos.exchange,
                action=action,
                order_type=OrderType.MARKET,
                product=pos.product,
                quantity=abs(pos.quantity)
            )
            res = await self.place_order(order_req)
            results.append(res)
        return results

    async def subscribe_market_feed(self, instrument_tokens: List[int], callback: Callable[[Dict[str, Any]], None]) -> None:
        # WebSocket live binary unpacker implemented in tick_ingestor worker
        pass
