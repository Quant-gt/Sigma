# apps/api/main.py
# SigmaSpire Control Plane API Root

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis.asyncio as redis

from apps.api.app.routers.backtest import router as backtest_router
from apps.api.app.routers.deployments import router as deployments_router
from apps.api.app.routers.marketplace import router as marketplace_router
from apps.api.app.routers.risk import router as risk_router
from apps.api.app.routers.scanner import router as scanner_router
from apps.api.app.routers.ai_copilot import router as ai_copilot_router
from apps.api.app.routers.vibe import router as vibe_router
from apps.api.app.routers.super_admin import router as super_admin_router
from apps.api.app.routers.citadel import router as citadel_router
from apps.api.app.middleware.sebi_guards import SEBIComplianceMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize shared Redis connection pool
    app.state.redis = redis.Redis(host="localhost", port=6379, db=0, decode_responses=False)
    yield
    # Shutdown: Close Redis connection pool
    await app.state.redis.aclose()


app = FastAPI(
    title="SigmaSpire Control Plane API",
    description="Enterprise Algorithmic Trading & Strategy Automation SaaS for Indian Capital Markets (NSE/BSE).",
    version="2.0.0",
    lifespan=lifespan
)

# CORS Middleware for Next.js 15 Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://app.sigmaspire.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SEBI 2026 Compliance Middleware (Kill Switch, 9-OPS, 16:05 IST Session Expiry)
app.add_middleware(SEBIComplianceMiddleware)

# Mount Modular Routers
app.include_router(risk_router)
app.include_router(backtest_router)
app.include_router(scanner_router)
app.include_router(deployments_router)
app.include_router(marketplace_router)
app.include_router(ai_copilot_router)
app.include_router(vibe_router)
app.include_router(super_admin_router)
app.include_router(citadel_router)


@app.get("/health", tags=["System Health"])
async def health_check():
    return {
        "status": "HEALTHY",
        "service": "SigmaSpire Control Plane",
        "sebiComplianceEngine": "ACTIVE",
        "version": "2.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
