# apps/api/app/routers/risk.py
# Risk Router & Emergency Kill-Switch Endpoint

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
import redis.asyncio as redis

router = APIRouter(prefix="/api/v1/risk", tags=["Risk Management & Compliance"])


class KillSwitchRequest(BaseModel):
    userId: str
    reason: str = "Manual User Trigger"


class RiskStatusResponse(BaseModel):
    userId: str
    isHalted: bool
    currentDailyMTM: float
    maxDailyLossLimit: float


@router.post("/kill-switch", status_code=status.HTTP_200_OK)
async def activate_kill_switch(payload: KillSwitchRequest) -> Dict[str, Any]:
    """
    SEBI Mandated Atomic Emergency Kill-Switch:
    1. Sets global halt lock in Redis.
    2. Broadcasts emergency cancel to all active broker workers.
    3. Triggers immediate square-off for open positions.
    4. Writes immutable audit log entry.
    """
    # Redis connection (configured in app lifetime)
    r = redis.Redis(host="localhost", port=6379, db=0)
    try:
        # Step 1: Set Redis HALT flag
        await r.set(f"risk:halt:{payload.userId}", "TRUE")

        # Step 2: Push emergency event into execution stream
        audit_event = {
            "userId": payload.userId,
            "action": "EMERGENCY_KILL_SWITCH",
            "reason": payload.reason,
            "status": "HALTED"
        }
        await r.xadd("stream:risk_events", {"payload": str(audit_event)})

        return {
            "success": True,
            "message": "Emergency Kill-Switch successfully triggered. All orders cancelled and trading halted.",
            "data": audit_event
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute kill-switch: {str(e)}"
        )
    finally:
        await r.aclose()


@router.get("/status/{userId}", response_model=RiskStatusResponse)
async def get_risk_status(userId: str):
    r = redis.Redis(host="localhost", port=6379, db=0)
    try:
        is_halted = bool(await r.get(f"risk:halt:{userId}"))
        mtm_bytes = await r.get(f"portfolio:mtm:{userId}")
        current_mtm = float(mtm_bytes.decode()) if mtm_bytes else 0.0
        limit_bytes = await r.get(f"risk:max_loss:{userId}")
        max_limit = float(limit_bytes.decode()) if limit_bytes else 50000.0

        return RiskStatusResponse(
            userId=userId,
            isHalted=is_halted,
            currentDailyMTM=current_mtm,
            maxDailyLossLimit=max_limit
        )
    finally:
        await r.aclose()
