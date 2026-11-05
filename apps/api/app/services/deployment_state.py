# apps/api/app/services/deployment_state.py
# Strategy Deployment State Machine & Pre-Flight Gatekeeper

from datetime import datetime, time, timezone, timedelta
from enum import Enum
from typing import Dict, Optional

IST = timezone(timedelta(hours=5, minutes=30))


class DeploymentStatus(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    KILLED_BY_RISK = "KILLED_BY_RISK"


class DeploymentStateException(Exception):
    pass


class DeploymentStateMachine:
    """
    Guarantees safe state transitions for live strategy deployments.
    Enforces SEBI market hours and pre-flight risk checks before activating live routing.
    """

    ALLOWED_TRANSITIONS = {
        DeploymentStatus.STOPPED: [DeploymentStatus.STARTING],
        DeploymentStatus.STARTING: [DeploymentStatus.RUNNING, DeploymentStatus.STOPPED],
        DeploymentStatus.RUNNING: [DeploymentStatus.PAUSED, DeploymentStatus.STOPPED, DeploymentStatus.KILLED_BY_RISK],
        DeploymentStatus.PAUSED: [DeploymentStatus.RUNNING, DeploymentStatus.STOPPED, DeploymentStatus.KILLED_BY_RISK],
        DeploymentStatus.KILLED_BY_RISK: [DeploymentStatus.STOPPED],
    }

    @staticmethod
    def is_regular_trading_session() -> bool:
        """NSE/BSE normal market hours: 09:15 AM - 03:30 PM IST (Mon-Fri)."""
        now_ist = datetime.now(IST)
        if now_ist.weekday() >= 5: # Saturday or Sunday
            return False
        current_time = now_ist.time()
        return time(9, 15, 0) <= current_time <= time(15, 30, 0)

    @staticmethod
    def validate_transition(current_status: DeploymentStatus, target_status: DeploymentStatus) -> None:
        allowed = DeploymentStateMachine.ALLOWED_TRANSITIONS.get(current_status, [])
        if target_status not in allowed:
            raise DeploymentStateException(
                f"Illegal state transition from '{current_status.value}' to '{target_status.value}'."
            )

    @classmethod
    def can_start_live_deployment(
        cls,
        is_paper_trade: bool,
        is_broker_session_valid: bool,
        is_global_kill_switch_active: bool,
        current_daily_loss: float,
        max_daily_loss_limit: float
    ) -> Dict[str, bool]:
        """
        Pre-flight sanity check: validates all parameters before arming deployment.
        """
        checks = {
            "trading_hours_valid": cls.is_regular_trading_session() or is_paper_trade,
            "broker_session_valid": is_broker_session_valid or is_paper_trade,
            "kill_switch_inactive": not is_global_kill_switch_active,
            "daily_loss_within_limit": current_daily_loss > -abs(max_daily_loss_limit),
        }
        all_passed = all(checks.values())
        return {"passed": all_passed, "checks": checks}
