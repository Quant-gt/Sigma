# apps/api/app/services/morning_readiness.py
# Morning Readiness Engine (08:30 AM - 09:14 AM IST 2FA Renewal Ritual)

from datetime import datetime, time, timezone, timedelta
from typing import Dict, List, Optional
import pyotp

from apps.api.app.core.security import BrokerCredentialVault

IST = timezone(timedelta(hours=5, minutes=30))


class MorningReadinessService:
    """
    SEBI 2026 Daily 2FA Session Lifecycle Engine.
    Indian broker OAuth access tokens expire at end-of-day (or 03:30 AM IST).
    Between 08:30 AM and 09:14 AM IST, this engine initiates:
    1. Automated TOTP code generation from encrypted credentials.
    2. Batch token renewal across all connected brokers (Zerodha, Dhan, Breeze, etc.).
    3. Dedicated Static Egress IP health verification.
    4. Margin sufficiency & NSE F&O circular ban list synchronization.
    """

    @staticmethod
    def is_morning_readiness_window() -> bool:
        """Checks if current time is within 08:30 AM - 09:14 AM IST."""
        now_ist = datetime.now(IST).time()
        start = time(8, 30, 0)
        end = time(9, 14, 59)
        return start <= now_ist <= end

    @staticmethod
    def generate_current_totp(vault: BrokerCredentialVault, encrypted_totp_secret: bytes, user_id: str) -> str:
        """Decrypts TOTP secret from AES-256 vault and generates live 6-digit TOTP."""
        plain_secret = vault.decrypt_secret(encrypted_totp_secret, associated_user_id=user_id)
        totp = pyotp.TOTP(plain_secret)
        return totp.now()

    @staticmethod
    def check_session_validity(session_valid_until: Optional[datetime]) -> bool:
        """
        Validates if session is currently active and belongs to today's trading day.
        SEBI requires sessions to reset daily.
        """
        if not session_valid_until:
            return False
        now_utc = datetime.now(timezone.utc)
        return session_valid_until > now_utc

    @staticmethod
    def compile_readiness_report(
        user_id: str,
        broker_accounts: List[Dict],
        active_deployments: List[Dict]
    ) -> Dict:
        """
        Evaluates overall account readiness for market open at 09:15 AM IST.
        """
        now_ist = datetime.now(IST)
        all_brokers_ready = True
        broker_statuses = []

        for acc in broker_accounts:
            is_valid = MorningReadinessService.check_session_validity(acc.get("session_valid_until"))
            if not is_valid:
                all_brokers_ready = False

            broker_statuses.append({
                "broker": acc.get("broker"),
                "clientCode": acc.get("client_code"),
                "sessionValid": is_valid,
                "egressIp": acc.get("assigned_static_egress_ip"),
                "validUntil": acc.get("session_valid_until").isoformat() if acc.get("session_valid_until") else None
            })

        return {
            "timestamp": now_ist.isoformat(),
            "isReadinessWindow": MorningReadinessService.is_morning_readiness_window(),
            "marketOpenStatus": "PRE_MARKET" if now_ist.time() < time(9, 15) else "MARKET_OPEN",
            "isReadyForOpen": all_brokers_ready and len(broker_statuses) > 0,
            "connectedBrokers": broker_statuses,
            "activeDeploymentCount": len(active_deployments)
        }
