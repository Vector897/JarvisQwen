"""入站 HTTP 限流：按客户端 IP 的固定窗口计数，保护常驻控制平面小机免遭
公网扫描/请求洪水打爆。纯 ASGI 中间件（不包裹响应），因此不影响 /api/events 的
SSE 长连接。

与 core/scheduler/ratelimit.py 无关——那个是约束**出站** LLM 调用的令牌桶；
本模块约束的是**入站** HTTP 请求量。
"""
from __future__ import annotations

import time
from threading import Lock

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

_WINDOW = 60.0  # 秒；固定窗口长度


def _client_ip(scope: Scope) -> str:
    # 后端只经 web 层（Next rewrites）反代对外，真实客户端 IP 在 X-Forwarded-For 里。
    for name, value in scope.get("headers") or []:
        if name == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[0].strip()
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """每 IP 每 60s 窗口最多 rpm 次请求；超限返回 429 + Retry-After。"""

    def __init__(self, app: ASGIApp, rpm: int = 240,
                 exempt_prefixes: tuple[str, ...] = ("/healthz",)) -> None:
        self.app = app
        self.rpm = rpm
        self.exempt = exempt_prefixes
        self._hits: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def _check(self, ip: str) -> int:
        """返回本窗口内该 IP 的累计请求数（含本次）。"""
        now = time.monotonic()
        with self._lock:
            start, count = self._hits.get(ip, (now, 0))
            if now - start >= _WINDOW:
                start, count = now, 0
            count += 1
            self._hits[ip] = (start, count)
            if len(self._hits) > 10_000:  # 顺手驱逐过期条目，防内存无限增长
                cutoff = now - _WINDOW
                self._hits = {k: v for k, v in self._hits.items() if v[0] >= cutoff}
            return count

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.exempt):
            await self.app(scope, receive, send)
            return
        if self._check(_client_ip(scope)) > self.rpm:
            resp = JSONResponse(
                {"detail": "Too many requests, slow down."},
                status_code=429,
                headers={"Retry-After": str(int(_WINDOW))},
            )
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)
