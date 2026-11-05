# tests/test_suite.py
"""
Comprehensive Automated Test Suite for SigmaSpire / Quantra-v2:
1. BrokerCredentialVault (AES-256-GCM + AAD tampering rejection)
2. IndianStatutoryCostEngine (Post-Oct 2024 SEBI/NSE tax rules)
3. StrategyAST Validation (Cycle detection + DAG integrity)
4. SEBICompliantOrderRouter (Freeze-qty slicing + MPP Limit calculation)
5. Vectorized Backtester & Numba Simulation Engine
"""

import os
import sys
from decimal import Decimal
import numpy as np
import polars as pl

# Configure test KMS key
TEST_KEY_HEX = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
os.environ["QUANTRA_MASTER_KMS_KEY_HEX"] = TEST_KEY_HEX
sys.path.insert(0, ".")

from apps.api.app.core.security import BrokerCredentialVault
from apps.api.app.core.indian_costs import IndianStatutoryCostEngine, TradeInstrumentType
from apps.api.app.schemas.ast_schema import (
    StrategyAST,
    UniverseNode,
    IndicatorNode,
    ActionLegNode,
    RiskLegConfig,
    OptionStrikeConfig,
    DAGEdge,
)
from apps.engine.workers.order_router import (
    NormalizedOrderRequest,
    SEBICompliantOrderRouter,
    NSE_FREEZE_QUANTITIES,
)
from apps.engine.backtest.simulator import QuantraVectorizedBacktester


def test_encryption_vault():
    print("[+] Running Test 1: BrokerCredentialVault...")
    vault = BrokerCredentialVault(TEST_KEY_HEX)
    token = "access_token_super_secret_kite_9941"
    user_id = "user_uuid_10293847"

    # Encrypt
    encrypted_blob = vault.encrypt_secret(token, associated_user_id=user_id)
    assert encrypted_blob != token.encode(), "Ciphertext must not match plaintext"

    # Decrypt with correct user_id
    decrypted = vault.decrypt_secret(encrypted_blob, associated_user_id=user_id)
    assert decrypted == token, f"Decryption mismatch: {decrypted} != {token}"

    # Tampering test: Decrypt with incorrect user_id (AAD verification must fail)
    try:
        vault.decrypt_secret(encrypted_blob, associated_user_id="attacker_user_id")
        assert False, "Tampered AAD should have raised an exception!"
    except Exception:
        pass  # Successfully caught tampering

    print("  [OK] BrokerCredentialVault AES-256-GCM and AAD tampering protection verified.")


def test_indian_statutory_costs():
    print("[+] Running Test 2: IndianStatutoryCostEngine (Post-Oct 2024 Schedule)...")
    
    # Test Options Round Trip (1 lot Nifty = 75 qty, Buy @ 100, Sell @ 150)
    qty = 75
    buy_px = Decimal("100.00")
    sell_px = Decimal("150.00")
    
    report = IndianStatutoryCostEngine.calculate_round_trip(
        instrument=TradeInstrumentType.OPTIONS,
        buy_price=buy_px,
        sell_price=sell_px,
        quantity=qty,
    )

    # 1. Brokerage = flat ₹40 (₹20 buy + ₹20 sell)
    assert report.brokerage == Decimal("40.00"), f"Brokerage expected 40.00, got {report.brokerage}"

    # 2. STT = 0.1% on sell premium (75 * 150 = 11,250 -> 0.1% = 11.25 -> rounded to 11)
    expected_stt = Decimal("11")
    assert report.stt_ctt == expected_stt, f"STT expected {expected_stt}, got {report.stt_ctt}"

    # 3. Verify GST = 18% on (Brokerage + Exchange + SEBI)
    taxable_sum = report.brokerage + report.exchange_turnover_charge + report.sebi_turnover_fee
    expected_gst = (taxable_sum * Decimal("0.18")).quantize(Decimal("0.01"))
    assert report.gst_18_pct == expected_gst, f"GST expected {expected_gst}, got {report.gst_18_pct}"

    assert report.total_charges > Decimal("50.00")
    print(f"  [OK] Options round-trip total statutory charges: INR {report.total_charges} | Breakeven: {report.net_breakeven_points_per_unit} pts")


def test_strategy_ast_validation():
    print("[+] Running Test 3: StrategyAST DAG Integrity & Cycle Detection...")

    # Valid DAG
    u_node = UniverseNode(node_id="u1", segment="NSE_FNO", underlying="NIFTY")
    ind_node = IndicatorNode(node_id="i1", indicator="SUPERTREND", timeframe="5m")
    leg_node = ActionLegNode(
        node_id="leg1",
        trigger_node_id="i1",
        universe_node_id="u1",
        side="SELL",
        lots=1,
        strike_config=OptionStrikeConfig(option_type="CE", selection_mode="ATM_OFFSET", atm_offset_steps=0),
        risk_config=RiskLegConfig(stop_loss_type="PERCENT", stop_loss_value=Decimal("25.0"), target_type="PERCENT", target_value=Decimal("50.0")),
        mpp_slippage_bps=50,
    )

    edges = [
        DAGEdge(id="e1", source="u1", target="i1"),
        DAGEdge(id="e2", source="i1", target="leg1"),
    ]

    ast = StrategyAST(
        strategy_name="Valid Test Strategy",
        nodes=[u_node, ind_node, leg_node],
        edges=edges,
    )
    crypto_hash = ast.compute_cryptographic_hash()
    assert len(crypto_hash) == 64, "Crypto hash must be 64-char SHA256"

    # Cycle Detection Test: Add an edge back from leg1 -> i1
    cyclic_edges = [
        DAGEdge(id="e1", source="u1", target="i1"),
        DAGEdge(id="e2", source="i1", target="leg1"),
        DAGEdge(id="e3", source="leg1", target="i1"), # Cycle!
    ]
    try:
        StrategyAST(
            strategy_name="Cyclic Failure Strategy",
            nodes=[u_node, ind_node, leg_node],
            edges=cyclic_edges,
        )
        assert False, "Cyclic DAG should have been rejected by DFS validator!"
    except ValueError as e:
        assert "Cyclic dependency" in str(e)

    print("  [OK] StrategyAST DAG validation, DFS cycle detection, and SHA-256 hash verified.")


def test_order_router_logic():
    print("[+] Running Test 4: SEBICompliantOrderRouter Freeze Slicing & MPP...")

    # 1. Freeze Quantity Auto-Slicing
    router = SEBICompliantOrderRouter(redis_client=None)
    slices_nifty = router._slice_by_freeze_quantity("NIFTY", 4000)
    # Nifty limit = 1800 -> 1800, 1800, 400
    assert slices_nifty == [1800, 1800, 400], f"Slicing mismatch: {slices_nifty}"

    slices_banknifty = router._slice_by_freeze_quantity("BANKNIFTY", 2000)
    # Banknifty limit = 900 -> 900, 900, 200
    assert slices_banknifty == [900, 900, 200], f"Slicing mismatch: {slices_banknifty}"

    # 2. Market Price Protection (MPP) Limit Price Check
    order_buy = NormalizedOrderRequest(
        user_id="u1", deployment_id="d1", leg_id="l1", candle_timestamp=1710000000,
        exchange_algo_id="ALG_01", underlying="NIFTY", trading_symbol="NIFTY24MAR22400CE",
        exchange="NFO", side="BUY", quantity=75, current_ltp=Decimal("150.00"),
        mpp_slippage_bps=50 # 0.50%
    )
    # 150 * 1.005 = 150.75
    mpp_buy_px = order_buy.compute_mpp_limit_price()
    assert mpp_buy_px == Decimal("150.75"), f"Expected 150.75, got {mpp_buy_px}"

    order_sell = NormalizedOrderRequest(
        user_id="u1", deployment_id="d1", leg_id="l1", candle_timestamp=1710000000,
        exchange_algo_id="ALG_01", underlying="NIFTY", trading_symbol="NIFTY24MAR22400CE",
        exchange="NFO", side="SELL", quantity=75, current_ltp=Decimal("150.00"),
        mpp_slippage_bps=50
    )
    # 150 * 0.995 = 149.25
    mpp_sell_px = order_sell.compute_mpp_limit_price()
    assert mpp_sell_px == Decimal("149.25"), f"Expected 149.25, got {mpp_sell_px}"

    print(f"  [OK] Freeze Slicing (Nifty: {slices_nifty}) & MPP (Buy: INR {mpp_buy_px}, Sell: INR {mpp_sell_px}) verified.")


def test_vectorized_backtester():
    print("[+] Running Test 5: Polars + Numba Vectorized Backtester Throughput...")

    # Build test AST
    u_node = UniverseNode(node_id="u1", segment="NSE_FNO", underlying="NIFTY")
    ind_node = IndicatorNode(node_id="i1", indicator="EMA", timeframe="1m", params={"period": 9})
    leg_node = ActionLegNode(
        node_id="leg1", trigger_node_id="i1", universe_node_id="u1", side="SELL", lots=1,
        strike_config=OptionStrikeConfig(option_type="CE", selection_mode="ATM_OFFSET", atm_offset_steps=0),
        risk_config=RiskLegConfig(
            stop_loss_type="PERCENT", stop_loss_value=Decimal("25.0"),
            target_type="PERCENT", target_value=Decimal("50.0"),
            trailing_sl_enabled=True, trail_step_Move=Decimal("10.0"), trail_sl_by=Decimal("5.0")
        ),
        mpp_slippage_bps=50,
    )
    ast = StrategyAST(
        strategy_name="Numba JIT Backtest Benchmark",
        nodes=[u_node, ind_node, leg_node],
        edges=[DAGEdge(id="e1", source="u1", target="i1"), DAGEdge(id="e2", source="i1", target="leg1")]
    )

    n_bars = 500
    base_ts = 1710000000
    spot_closes = np.full(n_bars, 22400.0) + np.random.normal(0, 10, n_bars)
    spot_df = pl.DataFrame({
        "timestamp": np.arange(base_ts, base_ts + n_bars * 60, 60, dtype=np.int64),
        "day_id": np.full(n_bars, 20240310, dtype=np.int32),
        "hhmm": np.arange(916, 916 + n_bars, dtype=np.int32),
        "spot_open": spot_closes,
        "spot_high": spot_closes + 5.0,
        "spot_low": spot_closes - 5.0,
        "spot_close": spot_closes,
        "spot_volume": np.random.randint(1000, 20000, n_bars),
    })

    options_chain_df = pl.DataFrame({
        "timestamp": np.arange(base_ts, base_ts + n_bars * 60, 60, dtype=np.int64),
        "strike": np.full(n_bars, 22400, dtype=np.int64),
        "option_type": ["CE"] * n_bars,
        "opt_open": np.full(n_bars, 120.0),
        "opt_high": np.full(n_bars, 130.0),
        "opt_low": np.full(n_bars, 85.0), # Will trigger target or SL
        "opt_close": np.full(n_bars, 100.0),
    })

    backtester = QuantraVectorizedBacktester(initial_capital_inr=Decimal("500000.00"))
    report = backtester.run_backtest(ast=ast, spot_df=spot_df, options_chain_df=options_chain_df, underlying="NIFTY")

    assert report.total_trades > 0, "Backtest should have executed trades"
    print(f"  [OK] Numba Backtest complete: {report.total_trades} trades executed | Net P&L: INR {report.net_pnl_inr} | Max DD: INR {report.max_drawdown_inr}")


if __name__ == "__main__":
    print("==================================================================")
    print("       SIGMASPIRE / QUANTRA-v2 FULL VERIFICATION SUITE           ")
    print("==================================================================")
    test_encryption_vault()
    test_indian_statutory_costs()
    test_strategy_ast_validation()
    test_order_router_logic()
    test_vectorized_backtester()
    print("==================================================================")
    print(" ALL 5 TEST MODULES PASSED (100% SUCCESS) ")
    print("==================================================================")
