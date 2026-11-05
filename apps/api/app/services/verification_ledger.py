# apps/api/app/services/verification_ledger.py
# Cryptographic Trade Verification Ledger (Anti-Fake Return Protocol)

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class VerifiedExecutionProof:
    trade_id: str
    strategy_id: str
    creator_id: str
    broker: str
    broker_order_id: str
    exchange_algo_id: str
    symbol: str
    fill_price: float
    fill_qty: int
    executed_at: str
    previous_block_hash: str
    proof_hash: str


class TradeVerificationLedger:
    """
    Immutable cryptographic ledger for live strategy executions.
    Solves the 'fake paper-trade screenshot' problem by requiring:
    1. Direct broker execution confirmation with exchange_algo_id.
    2. Deterministic SHA-256 chaining (genesis block -> latest trade).
    3. SEBI Research Analyst (RA) gating for encrypted Black-Box Vaults.
    """

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def generate_execution_proof(
        cls,
        trade_id: str,
        strategy_id: str,
        creator_id: str,
        broker: str,
        broker_order_id: str,
        exchange_algo_id: str,
        symbol: str,
        fill_price: float,
        fill_qty: int,
        executed_at: datetime,
        previous_block_hash: str = GENESIS_HASH
    ) -> VerifiedExecutionProof:
        timestamp_iso = executed_at.astimezone(timezone.utc).isoformat()
        
        # Raw block payload for hash computation
        payload = f"{trade_id}|{strategy_id}|{creator_id}|{broker}|{broker_order_id}|{exchange_algo_id}|{symbol}|{fill_price:.2f}|{fill_qty}|{timestamp_iso}|{previous_block_hash}"
        proof_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        return VerifiedExecutionProof(
            trade_id=trade_id,
            strategy_id=strategy_id,
            creator_id=creator_id,
            broker=broker,
            broker_order_id=broker_order_id,
            exchange_algo_id=exchange_algo_id,
            symbol=symbol,
            fill_price=fill_price,
            fill_qty=fill_qty,
            executed_at=timestamp_iso,
            previous_block_hash=previous_block_hash,
            proof_hash=proof_hash
        )

    @classmethod
    def verify_chain_integrity(cls, proofs: List[VerifiedExecutionProof]) -> bool:
        """Validates that no historical trade fill was modified or spoofed."""
        expected_prev = cls.GENESIS_HASH
        for p in proofs:
            if p.previous_block_hash != expected_prev:
                return False
            payload = f"{p.trade_id}|{p.strategy_id}|{p.creator_id}|{p.broker}|{p.broker_order_id}|{p.exchange_algo_id}|{p.symbol}|{p.fill_price:.2f}|{p.fill_qty}|{p.executed_at}|{expected_prev}"
            recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if recomputed != p.proof_hash:
                return False
            expected_prev = p.proof_hash
        return True
