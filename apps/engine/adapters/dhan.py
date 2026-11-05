# apps/engine/adapters/dhan.py
# DhanHQ v2 Broker Adapter Implementation

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


class DhanHQAdapter(BrokerAdapter):
    BASE_URL = "https://api.dhan.co/v2"

    def __init__(self, client_id: str, access_token: str, egress_ip: str):
        super().__init__(client_id, egress_ip)
        self.access_token = access_token
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "access-token": self.access_token,
                "client-id": self.client_id,
                "Content-Type": "application/json",
            },
            timeout=5.0
        )

    async def authenticate_session(self, api_key: str, api_secret: str, request_token: str) -> Dict[str, Any]:
        return {"access_token": self.access_token, "status": "ACTIVE"}

    async def place_order(self, order: StandardOrderRequest) -> StandardOrderResponse:
        # Map generic fields to Dhan v2 API format
        dhan_action = "BUY" if order.action == OrderAction.BUY else "SELL"
        dhan_order_type = "LIMIT" if order.order_type == OrderType.LIMIT else "MARKET"
        dhan_product = "INTRADAY" if order.product == OrderProduct.MIS else "CNC"

        payload = {
            "dhanClientId": self.client_id,
            "transactionType": dhan_action,
            "exchangeSegment": "NSE_FNO" if "FUT" in order.symbol or "CE" in order.symbol or "PE" in order.symbol else "NSE_EQ",
            "productType": dhan_product,
            "orderType": dhan_order_type,
            "validity": "DAY",
            "securityId": order.symbol,
            "quantity": order.quantity,
            "price": order.price or 0.0,
            "triggerPrice": order.trigger_price or 0.0,
            "correlationId": order.tag or "SIGMASPIRE"
        }

        try:
            res = await self.client.post("/orders", json=payload)
            res_data = res.json()
            if res.status_code in (200, 201) and res_data.get("orderStatus") in ("TRANSIT", "PENDING", "CONFIRMED"):
                return StandardOrderResponse(
                    success=True,
                    broker_order_id=res_data.get("orderId"),
                    status=res_data.get("orderStatus"),
                    raw_response=res_data
                )
            return StandardOrderResponse(
                success=False,
                broker_order_id=None,
                status="REJECTED",
                message=res_data.get("remarks") or res_data.get("message"),
                raw_response=res_data
            )
        except Exception as e:
            return StandardOrderResponse(success=False, broker_order_id=None, status="NETWORK_ERROR", message=str(e))

    async def modify_order(self, broker_order_id: str, new_price: Optional[float] = None, new_qty: Optional[int] = None) -> StandardOrderResponse:
        payload = {"orderId": broker_order_id}
        if new_price is not None:
            payload["price"] = new_price
        if new_qty is not None:
            payload["quantity"] = new_qty
        try:
            res = await self.client.put(f"/orders/{broker_order_id}", json=payload)
            return StandardOrderResponse(
                success=(res.status_code == 200),
                broker_order_id=broker_order_id,
                status="MODIFIED" if res.status_code == 200 else "REJECTED",
                raw_response=res.json()
            )
        except Exception as e:
            return StandardOrderResponse(success=False, broker_order_id=broker_order_id, status="ERROR", message=str(e))

    async def cancel_order(self, broker_order_id: str) -> bool:
        try:
            res = await self.client.delete(f"/orders/{broker_order_id}")
            return res.status_code == 200
        except Exception:
            return False

    async def cancel_all_orders(self) -> List[str]:
        cancelled = []
        try:
            res = await self.client.get("/orders")
            if res.status_code == 200:
                orders = res.json()
                for ord in orders:
                    if ord.get("orderStatus") in ("PENDING", "TRIGGER_PENDING"):
                        oid = str(ord["orderId"])
                        if await self.cancel_order(oid):
                            cancelled.append(oid)
        except Exception:
            pass
        return cancelled

    async def get_positions(self) -> List[PositionInfo]:
        positions = []
        try:
            res = await self.client.get("/positions")
            if res.status_code == 200:
                for pos in res.json():
                    net_qty = int(pos.get("netQty", 0))
                    if net_qty != 0:
                        positions.append(PositionInfo(
                            symbol=pos.get("tradingSymbol", ""),
                            exchange=pos.get("exchangeSegment", "NSE"),
                            product=OrderProduct.MIS if pos.get("productType") == "INTRADAY" else OrderProduct.CNC,
                            quantity=net_qty,
                            buy_price=float(pos.get("buyAvg", 0.0)),
                            sell_price=float(pos.get("sellAvg", 0.0)),
                            ltp=float(pos.get("costPrice", 0.0)),
                            unrealized_pnl=float(pos.get("unrealizedProfit", 0.0)),
                            realized_pnl=float(pos.get("realizedProfit", 0.0))
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
                exchange="NSE",
                action=action,
                order_type=OrderType.MARKET,
                product=pos.product,
                quantity=abs(pos.quantity)
            )
            res = await self.place_order(order_req)
            results.append(res)
        return results

    async def subscribe_market_feed(self, instrument_tokens: List[int], callback: Callable[[Dict[str, Any]], None]) -> None:
        pass
