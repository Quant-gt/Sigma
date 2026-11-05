# packages/db/models.py
# SQLAlchemy 2.0 Async ORM Models mirroring 001_init_quantra_rls.sql

import enum
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    BigInteger,
    LargeBinary,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class BrokerType(str, enum.Enum):
    ZERODHA = "ZERODHA"
    DHAN = "DHAN"
    ANGELONE = "ANGELONE"
    FYERS = "FYERS"
    UPSTOX = "UPSTOX"
    ICICI_BREEZE = "ICICI_BREEZE"


class StrategyVisibility(str, enum.Enum):
    PRIVATE = "PRIVATE"
    WHITE_BOX_PUBLIC = "WHITE_BOX_PUBLIC"
    BLACK_BOX_RA_ONLY = "BLACK_BOX_RA_ONLY"


class OrderState(str, enum.Enum):
    PENDING_VALIDATION = "PENDING_VALIDATION"
    QUEUED = "QUEUED"
    ROUTED = "ROUTED"
    OPEN = "OPEN"
    PARTIAL_FILL = "PARTIAL_FILL"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    full_name = Column(Text, nullable=False)
    sebi_ra_number = Column(Text, unique=True, nullable=True)
    sebi_ra_verified = Column(Boolean, nullable=False, default=False)
    global_kill_switch_active = Column(Boolean, nullable=False, default=False)
    max_daily_loss_inr = Column(Numeric(14, 2), nullable=False, default=10000.00)
    max_orders_per_day = Column(Integer, nullable=False, default=300)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    broker_accounts = relationship("BrokerAccount", back_populates="user", cascade="all, delete-orphan")
    strategies = relationship("Strategy", back_populates="owner", cascade="all, delete-orphan")
    deployments = relationship("Deployment", back_populates="user", cascade="all, delete-orphan")


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    broker = Column(Enum(BrokerType, name="broker_type"), nullable=False)
    client_code = Column(Text, nullable=False)
    encrypted_api_key = Column(LargeBinary, nullable=False)
    encrypted_api_secret = Column(LargeBinary, nullable=False)
    encrypted_access_token = Column(LargeBinary, nullable=True)
    token_kms_key_id = Column(Text, nullable=False)
    assigned_static_egress_ip = Column(INET, nullable=False)
    session_valid_until = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="broker_accounts")


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    visibility = Column(Enum(StrategyVisibility, name="strategy_visibility"), nullable=False, default=StrategyVisibility.PRIVATE)
    current_version = Column(Integer, nullable=False, default=1)
    ast_payload = Column(JSONB, nullable=False)
    react_flow_viewport = Column(JSONB, nullable=False)
    ast_sha256_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="strategies")
    deployments = relationship("Deployment", back_populates="strategy")


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id", ondelete="RESTRICT"), nullable=False)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False)
    exchange_algo_id = Column(Text, nullable=False)
    lot_multiplier = Column(Integer, nullable=False, default=1)
    is_paper_trade = Column(Boolean, nullable=False, default=False)
    status = Column(String(32), nullable=False, default="STOPPED")
    daily_realized_pnl = Column(Numeric(14, 2), nullable=False, default=0.00)
    daily_unrealized_pnl = Column(Numeric(14, 2), nullable=False, default=0.00)
    max_drawdown_limit_inr = Column(Numeric(14, 2), nullable=False)
    deployed_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="deployments")
    strategy = relationship("Strategy", back_populates="deployments")


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    deployment_id = Column(UUID(as_uuid=True), ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False)
    broker_account_id = Column(UUID(as_uuid=True), ForeignKey("broker_accounts.id"), nullable=False)
    idempotency_key = Column(Text, unique=True, nullable=False)
    broker_order_id = Column(Text, nullable=True)
    exchange_algo_id = Column(Text, nullable=False)
    trading_symbol = Column(Text, nullable=False)
    exchange = Column(String(8), nullable=False)
    transaction_type = Column(String(4), nullable=False)
    quantity = Column(Integer, nullable=False)
    order_type = Column(String(8), nullable=False)
    limit_price = Column(Numeric(12, 2), nullable=False)
    trigger_price = Column(Numeric(12, 2), nullable=True)
    average_fill_price = Column(Numeric(12, 2), nullable=True)
    filled_quantity = Column(Integer, nullable=False, default=0)
    state = Column(Enum(OrderState, name="order_state"), nullable=False, default=OrderState.PENDING_VALIDATION)
    rejection_reason = Column(Text, nullable=True)
    statutory_charges_inr = Column(Numeric(10, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ComplianceAuditLog(Base):
    __tablename__ = "compliance_audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    event_type = Column(Text, nullable=False)
    egress_ip = Column(INET, nullable=False)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
