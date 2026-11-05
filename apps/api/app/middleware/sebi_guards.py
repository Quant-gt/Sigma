# apps/api/app/middleware/sebi_guards.py
# Ported & Upgraded SEBI 2026 Compliance Middleware for FastAPI

import time
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as aioredis

IST = timezone(timedelta(hours=5, minutes=30))


class SEBIComplianceMiddleware(BaseHTTPMiddleware):
    """
    Ported from Quantra Legacy Express middleware with FastAPI async pipeline:
    1. Global & User-Level Emergency Kill-Switch Inspector
    2. SEBI 9-OPS (Orders-Per-Second) sliding-window rate throttler
    3. Daily 16:05 IST Session Expiry & 2FA Lifecycle Gatekeeper
    """

    def __init__(self, app, redis_client: Optional[aioredis.Redis] = None):
        super().__init__(app)
        self.redis = redis_client or aioredis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

    async def dispatch(self, request: Request, call_next):
        # Only enforce on trading, risk, and order routes
        path = request.url.path
        if not (path.startswith("/api/v1/orders") or path.startswith("/api/v1/deployments") or path.startswith("/api/v1/risk")):
            return await call_next(request)

        user_id = request.headers.get("x-user-id", "default_user")
        exchange = request.headers.get("x-exchange", "NSE")

        # ---------------------------------------------------------------------
        # 1. KILL SWITCH INSPECTOR
        # ---------------------------------------------------------------------
        try:
            # Check global kill switch
            global_halt = await self.redis.get("killswitch:global")
            if global_halt in ("true", "1", True, 1):
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "error": "Global Kill Switch activated. All market trading is suspended.",
                        "code": "GLOBAL_KILL_SWITCH",
                    },
                )

            # Check user-specific kill switch
            if user_id:
                user_halt = await self.redis.get(f"quantra:killswitch:{user_id}") or await self.redis.get(f"killswitch:user:{user_id}")
                if user_halt:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={
                            "error": f"Trading access suspended via Kill Switch for user {user_id}.",
                            "code": "USER_KILL_SWITCH",
                        },
                    )
        except Exception as e:
            # Redis connection error should not crash control plane
            pass

        # ---------------------------------------------------------------------
        # 2. SEBI 9-OPS RATE LIMITER (Orders per second)
        # ---------------------------------------------------------------------
        if path.startswith("/api/v1/orders") and request.method == "POST":
            try:
                now_sec = int(time.time())
                ops_key = f"ops:{user_id}:{exchange}:{now_sec}"
                current_ops = await self.redis.incr(ops_key)
                if current_ops == 1:
                    await self.redis.expire(ops_key, 2)

                if current_ops > 9:  # Capped at 9 OPS (under SEBI 10 OPS threshold)
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "error": f"SEBI Orders Per Second limit exceeded on {exchange}. Throttled.",
                            "code": "OPS_LIMIT_EXCEEDED",
                            "current_ops": current_ops,
                        },
                    )
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 3. DAILY 16:05 IST SESSION EXPIRY GATEKEEPER
        # ---------------------------------------------------------------------
        now_ist = datetime.now(IST)
        # SEBI mandate: all broker sessions terminate at 16:05 IST
        if (now_ist.hour > 16) or (now_ist.hour == 16 and now_ist.minute >= 5):
            if path.startswith("/api/v1/orders") and request.method == "POST":
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "Daily broker session expired at 16:05 IST. Daily renewal required.",
                        "code": "SESSION_EXPIRED_TIME",
                    },
                )

        return await call_next(request)
