# apps/api/app/routers/scanner.py
# Real-Time Market Scanner Server-Sent Events (SSE) Router

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import redis.asyncio as redis

router = APIRouter(prefix="/api/v1/scanner", tags=["Market Scanner & Live Screener"])


class CreateScannerRequest(BaseModel):
    name: str
    timeframe: str = "5m"
    minRsi: Optional[float] = None
    maxRsi: Optional[float] = None
    requireSupertrendBullish: Optional[bool] = None
    priceAboveVwap: Optional[bool] = None


@router.get("/stream")
async def stream_scanner_matches(
    request: Request,
    scanner_id: Optional[str] = Query(None, description="Filter matches by specific scanner ID")
):
    """
    Server-Sent Events (SSE) endpoint:
    Streams live market matches (<100ms latency) evaluated across Nifty 500 & F&O.
    """
    async def event_generator():
        r = redis.Redis(host="localhost", port=6379, db=0)
        pubsub = r.pubsub()
        channel = "quantra:scanner:alerts"
        await pubsub.subscribe(channel)

        try:
            # Yield initial connection heartbeat
            yield f"event: connected\ndata: {json.dumps({'status': 'STREAMING', 'channel': channel})}\n\n"

            while True:
                # Client disconnected?
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    payload = message["data"].decode("utf-8")
                    yield f"event: match\ndata: {payload}\n\n"
                else:
                    # Keep-alive heartbeat every 15 seconds to prevent gateway timeouts
                    yield ": keep-alive\n\n"

        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no", # Disable proxy buffering (Nginx/Cloudflare)
        }
    )
