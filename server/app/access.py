"""可选访问码网关（公网演示用）。

设置环境变量 AAOS_ACCESS_CODE 后，所有 /api 请求必须携带该码，否则 401：
  - Cookie: aaos_access=<code>（前端从 ?k=<code> 魔法链接自动写入）
  - 或查询串 ?k=<code>
  - 或请求头 X-Access-Code: <code>
不设置（默认空）则完全开放，不影响本地开发。纯 ASGI 中间件，不影响 SSE。

这是防"陌生人烧你的 Key 额度"的真正闸门；入站限流只负责防洪水打爆机器。
"""
from __future__ import annotations

from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def _provided_code(scope: Scope) -> str:
    headers = {k: v for k, v in (scope.get("headers") or [])}
    # 1) X-Access-Code 头
    if b"x-access-code" in headers:
        return headers[b"x-access-code"].decode("latin-1").strip()
    # 2) ?k= 查询串
    qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
    if qs.get("k"):
        return qs["k"][0].strip()
    # 3) aaos_access cookie
    cookie = headers.get(b"cookie", b"").decode("latin-1")
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == "aaos_access":
            return value.strip()
    return ""


class AccessGateMiddleware:
    """AAOS_ACCESS_CODE 非空时，未带正确码的 /api 请求一律 401。"""

    def __init__(self, app: ASGIApp, code: str,
                 exempt_prefixes: tuple[str, ...] = ("/healthz",)) -> None:
        self.app = app
        self.code = code
        self.exempt = exempt_prefixes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.code:
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        if any(path.startswith(p) for p in self.exempt):
            await self.app(scope, receive, send)
            return
        if _provided_code(scope) != self.code:
            resp = JSONResponse({"detail": "Access code required"}, status_code=401)
            await resp(scope, receive, send)
            return
        await self.app(scope, receive, send)
