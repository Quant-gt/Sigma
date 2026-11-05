# apps/engine/adapters/base.py
# Unified BrokerAdapter Abstract Base Class for Indian Capital Markets

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class OrderAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderProduct(str, Enum):
    MIS = "MIS"   # Intraday
    CNC = "CNC"   # Cash & Carry (Delivery)
    NRML = "NRML" # Normal (F&O overnight)


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


@dataclass
class StandardOrderRequest:
    symbol: str
    exchange: str # "NSE" or "BSE"
    action: OrderAction
    order_type: OrderType
    product: OrderProduct
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    disclosed_quantity: int = 0
    tag: Optional[str] = None # SEBI Algo ID tag


@dataclass
class StandardOrderResponse:
    success: bool
    broker_order_id: Optional[str]
    status: str
    message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class PositionInfo:
    symbol: str
    exchange: str
    product: OrderProduct
    quantity: int
    buy_price: float
    sell_price: float
    ltp: float
    unrealized_pnl: float
    realized_pnl: float


class BrokerAdapter(ABC):
    """
    Abstract interface unifying Zerodha Kite Connect, Dhan HQ, ICICI Breeze,
    Angel One SmartAPI, Fyers, and Upstox.
    """

    def __init__(self, client_id: str, egress_ip: str):
        self.client_id = client_id
        self.egress_ip = egress_ip

    @abstractmethod
    async def authenticate_session(self, api_key: str, api_secret: str, request_token: str) -> Dict[str, Any]:
        """Exchanges daily 2FA request token for an active access token."""
        pass

    @abstractmethod
    async def place_order(self, order: StandardOrderRequest) -> StandardOrderResponse:
        """Submits an order through the broker's API."""
        pass

    @abstractmethod
    async def modify_order(self, broker_order_id: str, new_price: Optional[float] = None, new_qty: Optional[int] = None) -> StandardOrderResponse:
        """Modifies price or quantity of an open trigger/limit order."""
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancels a single pending order."""
        pass

    @abstractmethod
    async def cancel_all_orders(self) -> List[str]:
        """Emergency method: Cancels all open orders across the account."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[PositionInfo]:
        """Fetches active day & overnight open positions."""
        pass

    @abstractmethod
    async def square_off_all_positions(self) -> List[StandardOrderResponse]:
        """Emergency method: Closes out all open positions at market/protected limit."""
        pass

    @abstractmethod
    async def subscribe_market_feed(self, instrument_tokens: List[int], callback: Callable[[Dict[str, Any]], None]) -> None:
        """Streams live tick data via broker WebSocket."""
        pass
