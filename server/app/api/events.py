"""SSE event stream: task progress, ETA updates, budget alerts, briefing pushes, approval notifications."""
from __future__ import annotations

import asyncio
import queue

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ..auth import current_user
from ..core.bus import EventBus, bus
from ..models import User

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events")
async def events(user: User = Depends(current_user)):
    q = bus.subscribe()

    async def stream():
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                try:
                    msg = await asyncio.to_thread(q.get, True, 25)
                    yield EventBus.sse_format(msg)
                except queue.Empty:
                    yield ": keepalive\n\n"  # heartbeat to prevent reverse-proxy timeout
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
