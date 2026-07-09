"""Inbound HTTP rate limiting: fixed-window counting per client IP, protecting the
always-on control-plane box from being overwhelmed by public scanning / request floods.
Pure ASGI middleware (does not wrap responses), so it does not affect the long-lived
SSE connection of /api/events.

Unrelated to core/scheduler/ratelimit.py — that one is a token bucket constraining
**outbound** LLM calls; this module constrains **inbound** HTTP request volume.

Over-limit events (429) are recorded to ./data/ratelimit.log for monitoring public scanning/attacks.
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from threading import Lock

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .config import config

_WINDOW = 60.0  # seconds; fixed-window length


def _client_ip(scope: Scope) -> str:
    # The backend is only exposed via the web layer (Next rewrites) reverse proxy, so the real client IP is in X-Forwarded-For.
    for name, value in scope.get("headers") or []:
        if name == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """At most rpm requests per IP per 60s window; over-limit returns 429 + Retry-After."""

    def __init__(self, app: ASGIApp, rpm: int = 240,
                 exempt_prefixes: tuple[str, ...] = ("/healthz",)) -> None:
        self.app = app
        self.rpm = rpm
        self.exempt = exempt_prefixes
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def _check(self, ip: str, path: str = "") -> int:
        """Return the cumulative request count for this IP within the current window (including this one)."""
        now = time.monotonic()
        with self._lock:
            start, count = self._hits.get(ip, (now, 0))
            if now - start >= _WINDOW:
                start, count = now, 0
            count += 1
            self._hits[ip] = (start, count)
            if len(self._hits) > 10_000:  # opportunistically evict expired entries to prevent unbounded memory growth
                cutoff = now - _WINDOW
                self._hits = {k: v for k, v in self._hits.items() if v[0] >= cutoff}

            # Log when over the limit
            if count > self.rpm:
                self._log_throttle(ip, path, count)
            return count

    def _log_throttle(self, ip: str, path: str, count: int) -> None:
        """Record the rate-limit event to ./data/ratelimit.log (to help monitor scanning/attacks)."""
        try:
            logfile = config.data_dir / "ratelimit.log"
            event = {
                "ts": datetime.utcnow().isoformat() + "Z",
                "ip": ip,
                "path": path,
                "request_count": count,
                "limit": self.rpm,
            }
            with open(logfile, "a") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass  # a log write failure should never affect the request

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.exempt):
            await self.app(scope, receive, send)
            return
        ip = _client_ip(scope)
        if self._check(ip, path) > self.rpm:
            resp = JSONResponse(
                {"detail": "Too many requests, slow down."},
                status_code=429,
                headers={"Retry-After": str(int(_WINDOW))},
            )
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)
