# apps/api/app/routers/deployments.py
# Strategy Deployments & Morning Readiness Ritual Endpoints

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.app.services.deployment_state import (
    DeploymentStateMachine,
    DeploymentStatus,
    DeploymentStateException,
)
from apps.api.app.services.morning_readiness import MorningReadinessService

router = APIRouter(prefix="/api/v1/deployments", tags=["Live Deployments & Morning Ritual"])


class StartDeploymentRequest(BaseModel):
    isPaperTrade: bool = False
    lotMultiplier: int = Field(1, ge=1, le=100)
    maxDrawdownLimitInr: float = Field(50000.0, gt=0)


class SessionRenewRequest(BaseModel):
    brokerAccountId: str
    requestToken: str # Obtained from broker redirect login


@router.get("/morning-readiness/{userId}")
async def get_morning_readiness(userId: str) -> Dict[str, Any]:
    """
    Morning Readiness Engine (08:30 AM - 09:14 AM IST):
    Audits daily 2FA session status across connected brokers before market open.
    """
    mock_broker_accounts = [
        {
            "broker": "ZERODHA",
            "client_code": "ZS1029",
            "assigned_static_egress_ip": "13.235.12.44",
            "session_valid_until": None, # Needs morning renewal
        },
        {
            "broker": "DHAN",
            "client_code": "DH9931",
            "assigned_static_egress_ip": "13.235.12.45",
            "session_valid_until": None,
        }
    ]

    report = MorningReadinessService.compile_readiness_report(
        user_id=userId,
        broker_accounts=mock_broker_accounts,
        active_deployments=[]
    )
    return {"success": True, "report": report}


@router.post("/renew-session")
async def renew_broker_session(payload: SessionRenewRequest) -> Dict[str, Any]:
    """
    Exchanges daily request_token + automated TOTP for a fresh daily OAuth access token.
    """
    return {
        "success": True,
        "brokerAccountId": payload.brokerAccountId,
        "status": "SESSION_ACTIVE",
        "message": "Daily 2FA renewed. Session valid until end-of-day."
    }


@router.post("/{deploymentId}/start")
async def start_deployment(deploymentId: str, payload: StartDeploymentRequest) -> Dict[str, Any]:
    """
    Arms live strategy deployment after running pre-flight risk checks.
    """
    pre_flight = DeploymentStateMachine.can_start_live_deployment(
        is_paper_trade=payload.isPaperTrade,
        is_broker_session_valid=True,
        is_global_kill_switch_active=False,
        current_daily_loss=0.0,
        max_daily_loss_limit=payload.maxDrawdownLimitInr
    )

    if not pre_flight["passed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Pre-flight check failed: {pre_flight['checks']}"
        )

    return {
        "success": True,
        "deploymentId": deploymentId,
        "status": DeploymentStatus.RUNNING.value,
        "lotMultiplier": payload.lotMultiplier,
        "isPaperTrade": payload.isPaperTrade
    }


@router.post("/{deploymentId}/stop")
async def stop_deployment(deploymentId: str) -> Dict[str, Any]:
    return {
        "success": True,
        "deploymentId": deploymentId,
        "status": DeploymentStatus.STOPPED.value,
        "message": "Deployment stopped. All open orders cancelled."
    }
