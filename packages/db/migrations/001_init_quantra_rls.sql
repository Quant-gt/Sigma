-- packages/db/migrations/001_init_quantra_rls.sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. ENUMS
DO $$ BEGIN
    CREATE TYPE broker_type AS ENUM ('ZERODHA', 'DHAN', 'ANGELONE', 'FYERS', 'UPSTOX', 'ICICI_BREEZE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE strategy_visibility AS ENUM ('PRIVATE', 'WHITE_BOX_PUBLIC', 'BLACK_BOX_RA_ONLY');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE order_state AS ENUM (
        'PENDING_VALIDATION', 'QUEUED', 'ROUTED', 'OPEN', 
        'PARTIAL_FILL', 'COMPLETE', 'REJECTED', 'CANCELLED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 2. USERS & SEBI COMPLIANCE PROFILE
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    sebi_ra_number TEXT UNIQUE, -- Required ONLY if publishing BLACK_BOX_RA_ONLY strategies
    sebi_ra_verified BOOLEAN NOT NULL DEFAULT FALSE,
    global_kill_switch_active BOOLEAN NOT NULL DEFAULT FALSE,
    max_daily_loss_inr NUMERIC(14, 2) NOT NULL DEFAULT 10000.00,
    max_orders_per_day INT NOT NULL DEFAULT 300,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. ZERO-TRUST BROKER CREDENTIALS VAULT (AES-256-GCM Encrypted)
CREATE TABLE IF NOT EXISTS broker_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    broker broker_type NOT NULL,
    client_code TEXT NOT NULL,
    -- Encrypted blobs: format is base64(nonce + ciphertext + tag)
    encrypted_api_key BYTEA NOT NULL,
    encrypted_api_secret BYTEA NOT NULL,
    encrypted_access_token BYTEA,
    token_kms_key_id TEXT NOT NULL,
    -- SEBI Static IP & Daily 2FA Session Tracking
    assigned_static_egress_ip INET NOT NULL,
    session_valid_until TIMESTAMPTZ, -- Resets daily at 03:30 AM IST per SEBI mandate
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, broker, client_code)
);

-- 4. STRATEGIES & VERSIONED JSON AST
CREATE TABLE IF NOT EXISTS strategies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    visibility strategy_visibility NOT NULL DEFAULT 'PRIVATE',
    current_version INT NOT NULL DEFAULT 1,
    ast_payload JSONB NOT NULL,          -- Validated Canonical JSON AST
    react_flow_viewport JSONB NOT NULL,  -- UI layout positions for React Flow
    ast_sha256_hash TEXT NOT NULL,       -- Cryptographic proof of strategy logic
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. LIVE STRATEGY DEPLOYMENTS
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_id UUID NOT NULL REFERENCES strategies(id) ON DELETE RESTRICT,
    broker_account_id UUID NOT NULL REFERENCES broker_accounts(id) ON DELETE CASCADE,
    exchange_algo_id TEXT NOT NULL,      -- SEBI / Exchange tagged Algo ID
    lot_multiplier INT NOT NULL DEFAULT 1 CHECK (lot_multiplier >= 1 AND lot_multiplier <= 100),
    is_paper_trade BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL DEFAULT 'STOPPED' CHECK (status IN ('RUNNING', 'PAUSED', 'STOPPED', 'KILLED_BY_RISK')),
    daily_realized_pnl NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    daily_unrealized_pnl NUMERIC(14, 2) NOT NULL DEFAULT 0.00,
    max_drawdown_limit_inr NUMERIC(14, 2) NOT NULL,
    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. IDEMPOTENT ORDERS LEDGER
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    deployment_id UUID NOT NULL REFERENCES deployments(id) ON DELETE CASCADE,
    broker_account_id UUID NOT NULL REFERENCES broker_accounts(id),
    -- Deterministic idempotency key: sha256(deployment_id + leg_id + candle_ts + action)
    idempotency_key TEXT UNIQUE NOT NULL,
    broker_order_id TEXT,
    exchange_algo_id TEXT NOT NULL,
    trading_symbol TEXT NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange IN ('NSE', 'NFO', 'BSE', 'BFO')),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
    quantity INT NOT NULL CHECK (quantity > 0),
    order_type TEXT NOT NULL CHECK (order_type IN ('LIMIT', 'SL', 'SL-M')), -- Raw MARKET banned; auto-converted to MPP LIMIT
    limit_price NUMERIC(12, 2) NOT NULL,
    trigger_price NUMERIC(12, 2),
    average_fill_price NUMERIC(12, 2),
    filled_quantity INT NOT NULL DEFAULT 0,
    state order_state NOT NULL DEFAULT 'PENDING_VALIDATION',
    rejection_reason TEXT,
    statutory_charges_inr NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. IMMUTABLE REGULATORY AUDIT LOG (SEBI 5-Year Retention)
CREATE TABLE IF NOT EXISTS compliance_audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL, -- e.g., 'KILL_SWITCH_TRIGGERED', 'ORDER_ROUTED', '2FA_RENEWED'
    egress_ip INET NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- STRICT ROW-LEVEL SECURITY (RLS) ENFORCEMENT
-- ============================================================================
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE broker_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE strategies ENABLE ROW LEVEL SECURITY;
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_audit_logs ENABLE ROW LEVEL SECURITY;

-- Dynamic session helper: API sets `SET LOCAL app.current_user_id = '<uuid>';` per transaction
CREATE OR REPLACE FUNCTION current_app_user() RETURNS UUID AS $$
    SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID;
$$ LANGUAGE SQL STABLE;

DROP POLICY IF EXISTS users_self_policy ON users;
CREATE POLICY users_self_policy ON users
    USING (id = current_app_user());

DROP POLICY IF EXISTS broker_isolation_policy ON broker_accounts;
CREATE POLICY broker_isolation_policy ON broker_accounts
    USING (user_id = current_app_user());

DROP POLICY IF EXISTS strategy_access_policy ON strategies;
CREATE POLICY strategy_access_policy ON strategies
    USING (owner_id = current_app_user() OR visibility = 'WHITE_BOX_PUBLIC')
    WITH CHECK (owner_id = current_app_user());

DROP POLICY IF EXISTS deployment_isolation_policy ON deployments;
CREATE POLICY deployment_isolation_policy ON deployments
    USING (user_id = current_app_user());

DROP POLICY IF EXISTS order_isolation_policy ON orders;
CREATE POLICY order_isolation_policy ON orders
    USING (user_id = current_app_user());

DROP POLICY IF EXISTS audit_read_only_policy ON compliance_audit_logs;
CREATE POLICY audit_read_only_policy ON compliance_audit_logs
    FOR SELECT USING (user_id = current_app_user());
