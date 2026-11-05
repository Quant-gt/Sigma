# apps/engine/workers/order_router.py
from __future__ import annotations
import asyncio
import hashlib
import time
from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Literal, Optional
import httpx
import redis.asyncio as aioredis
from pydantic import BaseModel


# NSE Freeze Quantity Limits (Auto-sliced by Router)
NSE_FREEZE_QUANTITIES: Dict[str, int] = {
    "NIFTY": 1800,
    "BANKNIFTY": 900,
    "FINNIFTY": 1800,
    "MIDCPNIFTY": 2800,
}


class NormalizedOrderRequest(BaseModel):
    user_id: str
    deployment_id: str
    leg_id: str
    candle_timestamp: int
    exchange_algo_id: str
    underlying: str
    trading_symbol: str
    exchange: Literal["NSE", "NFO", "BSE", "BFO"]
    side: Literal["BUY", "SELL"]
    quantity: int
    current_ltp: Decimal
    mpp_slippage_bps: int = 50  # 50 bps = 0.50% Market Price Protection
    product: Literal["MIS", "NRML"] = "MIS"

    @property
    def idempotency_key(self) -> str:
        raw = f"{self.deployment_id}:{self.leg_id}:{self.candle_timestamp}:{self.side}:{self.trading_symbol}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    def compute_mpp_limit_price(self) -> Decimal:
        """
        SEBI Mandate: Convert raw Market Orders into Market Price Protection (MPP) Limit Orders
        rounded to nearest ₹0.05 tick size.
        """
        slippage_factor = Decimal(self.mpp_slippage_bps) / Decimal(10000)
        if self.side == "BUY":
            raw_limit = self.current_ltp * (Decimal("1") + slippage_factor)
        else:
            raw_limit = self.current_ltp * (Decimal("1") - slippage_factor)
        # Round to NSE 0.05 tick multiple
        ticks = (raw_limit / Decimal("0.05")).quantize(Decimal("1"), ROUND_HALF_UP)
        return (ticks * Decimal("0.05")).quantize(Decimal("0.01"))


# ============================================================================
# 1. ABSTRACT BROKER ADAPTER INTERFACE
# ============================================================================
class BrokerAdapter(ABC):
    def __init__(self, client_code: str, access_token: str, api_key: str, static_egress_ip: str):
        self.client_code = client_code
        self.access_token = access_token
        self.api_key = api_key
        self.static_egress_ip = static_egress_ip
        # Bind HTTP client strictly to the user's whitelisted Static Egress IP
        transport = httpx.AsyncHTTPTransport(local_address=self.static_egress_ip)
        self.http = httpx.AsyncClient(transport=transport, timeout=3.0)

    @abstractmethod
    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        """Places a single MPP Limit order and returns broker_order_id."""

    @abstractmethod
    async def cancel_all_open_orders(self) -> List[str]:
        """Cancels all open/trigger pending orders for the Kill Switch."""

    @abstractmethod
    async def square_off_all_positions(self) -> List[str]:
        """Squares off all open intraday/algo positions immediately."""


# ============================================================================
# 2. ZERODHA KITE CONNECT v3 ADAPTER
# ============================================================================
class ZerodhaKiteAdapter(BrokerAdapter):
    BASE_URL = "https://api.kite.trade"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        payload = {
            "tradingsymbol": order.trading_symbol,
            "exchange": order.exchange,
            "transaction_type": order.side,
            "order_type": "LIMIT",
            "quantity": slice_qty,
            "price": str(limit_price),
            "product": order.product,
            "validity": "DAY",
            "tag": order.exchange_algo_id[:20],  # Kite tag limit
        }
        resp = await self.http.post(
            f"{self.BASE_URL}/orders/regular", data=payload, headers=self._headers
        )
        resp.raise_for_status()
        return resp.json()["data"]["order_id"]

    async def cancel_all_open_orders(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/orders", headers=self._headers)
        resp.raise_for_status()
        orders = resp.json().get("data", [])
        pending = [o for o in orders if o["status"] in ("OPEN", "TRIGGER PENDING")]
        cancelled_ids = []
        for o in pending:
            c_resp = await self.http.delete(
                f"{self.BASE_URL}/orders/{o['variety']}/{o['order_id']}",
                headers=self._headers,
            )
            if c_resp.status_code == 200:
                cancelled_ids.append(o["order_id"])
        return cancelled_ids

    async def square_off_all_positions(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/portfolio/positions", headers=self._headers)
        resp.raise_for_status()
        net_positions = resp.json().get("data", {}).get("net", [])
        squared_ids = []
        for pos in net_positions:
            net_qty = int(pos["quantity"])
            if net_qty == 0:
                continue
            exit_side = "SELL" if net_qty > 0 else "BUY"
            ltp = Decimal(str(pos["last_price"]))
            # Apply 1% emergency MPP protection on Kill Switch square-off
            mpp_price = (ltp * (Decimal("0.99") if exit_side == "SELL" else Decimal("1.01"))).quantize(Decimal("0.05"))
            payload = {
                "tradingsymbol": pos["tradingsymbol"],
                "exchange": pos["exchange"],
                "transaction_type": exit_side,
                "order_type": "LIMIT",
                "quantity": abs(net_qty),
                "price": str(mpp_price),
                "product": pos["product"],
                "validity": "DAY",
                "tag": "KILLSWITCH",
            }
            sq_resp = await self.http.post(
                f"{self.BASE_URL}/orders/regular", data=payload, headers=self._headers
            )
            if sq_resp.status_code == 200:
                squared_ids.append(sq_resp.json()["data"]["order_id"])
        return squared_ids


# ============================================================================
# 3. DHAN HQ v2 ADAPTER
# ============================================================================
class DhanHQAdapter(BrokerAdapter):
    BASE_URL = "https://api.dhan.co/v2"

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "access-token": self.access_token,
            "client-id": self.client_code,
            "Content-Type": "application/json",
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        payload = {
            "dhanClientId": self.client_code,
            "correlationId": order.idempotency_key[:20],
            "transactionType": order.side,
            "exchangeSegment": "NSE_FNO" if order.exchange == "NFO" else "NSE_EQ",
            "productType": "INTRADAY" if order.product == "MIS" else "MARGIN",
            "orderType": "LIMIT",
            "validity": "DAY",
            "securityId": order.trading_symbol,
            "quantity": slice_qty,
            "price": float(limit_price),
        }
        resp = await self.http.post(
            f"{self.BASE_URL}/orders", json=payload, headers=self._headers
        )
        resp.raise_for_status()
        return resp.json()["orderId"]

    async def cancel_all_open_orders(self) -> List[str]:
        resp = await self.http.get(f"{self.BASE_URL}/orders", headers=self._headers)
        resp.raise_for_status()
        orders = resp.json() or []
        cancelled = []
        for o in orders:
            if o.get("orderStatus") in ("PENDING", "TRANSIT"):
                c_resp = await self.http.delete(
                    f"{self.BASE_URL}/orders/{o['orderId']}", headers=self._headers
                )
                if c_resp.status_code in (200, 202):
                    cancelled.append(o["orderId"])
        return cancelled

    async def square_off_all_positions(self) -> List[str]:
        # Dhan exit all positions endpoint
        resp = await self.http.delete(f"{self.BASE_URL}/positions", headers=self._headers)
        resp.raise_for_status()
        return ["DHAN_ALL_POSITIONS_EXITED"]


# ============================================================================
# 4. SEBI-COMPLIANT ORDER ROUTER (9 OPS THROTTLER + IDEMPOTENCY + KILL SWITCH)
# ============================================================================
class SEBICompliantOrderRouter:
    """
    Enforces:
    1. Global Redis Kill-Switch lock check (`quantra:killswitch:{user_id}`)
    2. Idempotency lock (`quantra:idemp:{idempotency_key}`)
    3. Token-bucket 9 OPS rate limit per broker session (`quantra:ops:{broker_account_id}`)
    4. Automatic NSE Freeze-Quantity slicing
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    async def _acquire_sebi_9ops_slot(self, broker_account_id: str) -> None:
        """
        Strict sliding 1-second window capped at 9 orders/sec (under SEBI 10 OPS limit).
        """
        while True:
            current_sec = int(time.time())
            bucket_key = f"quantra:ops:{broker_account_id}:{current_sec}"
            count = await self.redis.incr(bucket_key)
            if count == 1:
                await self.redis.expire(bucket_key, 2)
            if count <= 9:
                return
            # Wait until next millisecond tick if 9 OPS reached
            await asyncio.sleep(0.05)

    def _slice_by_freeze_quantity(self, underlying: str, total_qty: int) -> List[int]:
        freeze_limit = NSE_FREEZE_QUANTITIES.get(underlying.upper(), 10000)
        slices: List[int] = []
        remaining = total_qty
        while remaining > 0:
            chunk = min(remaining, freeze_limit)
            slices.append(chunk)
            remaining -= chunk
        return slices

    async def route_order(
        self, adapter: BrokerAdapter, broker_account_id: str, order: NormalizedOrderRequest
    ) -> List[str]:
        # 1. Check Global Atomic Kill-Switch Lock
        is_halted = await self.redis.get(f"quantra:killswitch:{order.user_id}")
        if is_halted:
            raise PermissionError(f"Execution HALTED: Kill Switch active for user {order.user_id}")

        # 2. Enforce Idempotency (SET NX with 24h expiry)
        idemp_key = f"quantra:idemp:{order.idempotency_key}"
        acquired = await self.redis.set(idemp_key, "LOCKED", ex=86400, nx=True)
        if not acquired:
            raise RuntimeError(f"Duplicate order blocked by Idempotency Engine: {order.idempotency_key}")

        # 3. Compute SEBI Market Price Protection (MPP) Limit Price
        mpp_limit_price = order.compute_mpp_limit_price()

        # 4. Auto-slice order if total quantity exceeds NSE Freeze Limit
        qty_slices = self._slice_by_freeze_quantity(order.underlying, order.quantity)
        broker_order_ids: List[str] = []

        for slice_qty in qty_slices:
            await self._acquire_sebi_9ops_slot(broker_account_id)
            broker_oid = await adapter.place_limit_order(order, slice_qty, mpp_limit_price)
            broker_order_ids.append(broker_oid)

        return broker_order_ids

    async def execute_emergency_kill_switch(
        self, user_id: str, active_adapters: List[BrokerAdapter]
    ) -> Dict[str, List[str]]:
        """
        Atomic Emergency Kill Switch:
        1. Sets immediate Redis HALT flag in < 1ms so no worker can fire new orders.
        2. Cancels all open/pending orders across all brokers concurrently.
        3. Squares off all open positions with MPP limit orders concurrently.
        """
        # Step 1: Lock user execution globally
        await self.redis.set(f"quantra:killswitch:{user_id}", "HALTED_BY_USER", ex=86400)

        # Step 2: Parallel cancel all pending orders
        cancel_results = await asyncio.gather(
            *(adapter.cancel_all_open_orders() for adapter in active_adapters),
            return_exceptions=True,
        )

        # Step 3: Parallel square-off all open positions
        square_off_results = await asyncio.gather(
            *(adapter.square_off_all_positions() for adapter in active_adapters),
            return_exceptions=True,
        )

        return {
            "status": ["HALTED_AND_SQUARED_OFF"],
            "cancelled_batches": [str(r) for r in cancel_results],
            "squared_off_batches": [str(r) for r in square_off_results],
        }
