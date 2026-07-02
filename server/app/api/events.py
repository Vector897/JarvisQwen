"""SSE 事件流：任务进度、ETA 更新、预算告警、简报推送、审批通知。"""
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
                    yield ": keepalive\n\n"  # 心跳防反代超时
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
