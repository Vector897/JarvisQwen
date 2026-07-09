"""In-process event bus: worker threads publish, SSE subscribers consume (thread-safe)."""
from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=500)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def publish(self, event_type: str, data: dict[str, Any]) -> None:
        msg = {"type": event_type, "ts": time.time(), **data}
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(msg)
            except queue.Full:
                pass  # drop for slow consumers; state is reconciled via REST after SSE reconnects

    @staticmethod
    def sse_format(msg: dict[str, Any]) -> str:
        return f"event: {msg['type']}\ndata: {json.dumps(msg, ensure_ascii=False)}\n\n"


bus = EventBus()
