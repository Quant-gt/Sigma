# apps/engine/adapters/breeze.py
from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Dict, List
from apps.engine.workers.order_router import BrokerAdapter, NormalizedOrderRequest


class ICICIBreezeAdapter(BrokerAdapter):
    """
    Production ICICI Securities Breeze REST & WebSocket Adapter.
    Enforces:
    - Static Egress IP binding (mandatory per SEBI / ICICI Direct April 2026 rules)
    - SHA-256 X-Checksum request signing
    - Automatic NSE Symbol -> ISEC Stock Code translation
    """
    BASE_URL = "https://api.icicidirect.com/breezeapi/api/v1"

    # Canonical NSE -> ISEC Security Master mapping cache (hydrated daily at 08:00 AM IST)
    NSE_TO_ISEC_CODE: Dict[str, str] = {
        "RELIANCE": "RELIND",
        "HDFCBANK": "HDFBAN",
        "INFY": "INFTEC",
        "ICICIBANK": "ICIBAN",
        "TCS": "TCS",
        "SBIN": "STABAN",
        "NIFTY": "NIFTY",
        "BANKNIFTY": "CNXBAN",
        "FINNIFTY": "NIFFIN",
    }

    def __init__(
        self,
        client_code: str,
        access_token: str,   # Breeze Session Token generated daily via 2FA login
        api_key: str,        # Breeze App Key
        api_secret: str,     # Breeze Secret Key for SHA256 Checksum signing
        static_egress_ip: str,
    ):
        super().__init__(client_code, access_token, api_key, static_egress_ip)
        self.api_secret = api_secret

    def _generate_breeze_headers(self, body_dict: Dict) -> Dict[str, str]:
        """Generates ICICI Breeze Triple-Secure SHA-256 Checksum Headers."""
        iso_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        payload_str = json.dumps(body_dict, separators=(",", ":"))
        raw_signature = f"{iso_ts}{payload_str}{self.api_secret}"
        checksum = hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()

        return {
            "Content-Type": "application/json",
            "X-Checksum": f"token {checksum}",
            "X-Timestamp": iso_ts,
            "X-AppKey": self.api_key,
            "X-SessionToken": self.access_token,
        }

    async def place_limit_order(
        self, order: NormalizedOrderRequest, slice_qty: int, limit_price: Decimal
    ) -> str:
        isec_stock_code = self.NSE_TO_ISEC_CODE.get(order.underlying.upper(), order.underlying.upper())
        is_fno = order.exchange in ("NFO", "BFO")

        body = {
            "stock_code": isec_stock_code,
            "exchange_code": order.exchange,
            "product": "options" if is_fno else "intraday",
            "action": order.side.lower(),  # "buy" or "sell"
            "order_type": "limit",
            "stoploss": "0",
            "quantity": str(slice_qty),
            "price": str(limit_price),
            "validity": "day",
            "disclosed_quantity": "0",
            "user_remark": order.exchange_algo_id[:20],
        }
        headers = self._generate_breeze_headers(body)
        resp = await self.http.post(
            f"{self.BASE_URL}/order",
            content=json.dumps(body, separators=(",", ":")),
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("Status") != 200 or not data.get("Success"):
            raise RuntimeError(f"ICICI Breeze Order Rejected: {data.get('Error')}")
        return str(data["Success"]["order_id"])

    async def cancel_all_open_orders(self) -> List[str]:
        body = {"exchange_code": "NFO", "from_date": "", "to_date": ""}
        headers = self._generate_breeze_headers(body)
        resp = await self.http.get(
            f"{self.BASE_URL}/order",
            headers=headers,
        )
        resp.raise_for_status()
        orders = resp.json().get("Success") or []
        cancelled_ids: List[str] = []

        for o in orders:
            if o.get("status") in ("Ordered", "Pending", "Requested"):
                cancel_body = {
                    "order_id": o["order_id"],
                    "exchange_code": o.get("exchange_code", "NFO"),
                }
                c_headers = self._generate_breeze_headers(cancel_body)
                c_resp = await self.http.delete(
                    f"{self.BASE_URL}/order",
                    content=json.dumps(cancel_body, separators=(",", ":")),
                    headers=c_headers,
                )
                if c_resp.status_code == 200:
                    cancelled_ids.append(str(o["order_id"]))
        return cancelled_ids

    async def square_off_all_positions(self) -> List[str]:
        body = {}
        headers = self._generate_breeze_headers(body)
        resp = await self.http.get(f"{self.BASE_URL}/portfoliopositions", headers=headers)
        resp.raise_for_status()
        positions = resp.json().get("Success") or []
        squared_ids: List[str] = []

        for pos in positions:
            qty = int(pos.get("quantity", 0))
            if qty == 0:
                continue
            exit_action = "sell" if qty > 0 else "buy"
            ltp = Decimal(str(pos.get("ltp", "100.00")))
            mpp_price = (
                ltp * (Decimal("0.99") if exit_action == "sell" else Decimal("1.01"))
            ).quantize(Decimal("0.05"))

            sq_body = {
                "stock_code": pos["stock_code"],
                "exchange_code": pos["exchange_code"],
                "product": pos["product_type"].lower(),
                "action": exit_action,
                "order_type": "limit",
                "quantity": str(abs(qty)),
                "price": str(mpp_price),
                "validity": "day",
                "user_remark": "KILLSWITCH",
            }
            sq_headers = self._generate_breeze_headers(sq_body)
            sq_resp = await self.http.post(
                f"{self.BASE_URL}/order",
                content=json.dumps(sq_body, separators=(",", ":")),
                headers=sq_headers,
            )
            if sq_resp.status_code == 200 and sq_resp.json().get("Success"):
                squared_ids.append(str(sq_resp.json()["Success"]["order_id"]))

        return squared_ids
