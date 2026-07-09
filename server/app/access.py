"""Optional access-code gateway (for public demos).

When the AAOS_ACCESS_CODE environment variable is set, every /api request must
carry the code or it gets a 401:
  - Cookie: aaos_access=<code> (written automatically by the frontend from the ?k=<code> magic link)
  - or query string ?k=<code>
  - or request header X-Access-Code: <code>
When unset (empty by default) it is fully open and does not affect local development.
Pure ASGI middleware, so it does not interfere with SSE.

This is the real gate that stops "strangers burning your key quota"; inbound rate
limiting only guards against floods overwhelming the machine.
"""
from __future__ import annotations

from urllib.parse import parse_qs

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


def _provided_code(scope: Scope) -> str:
    headers = {k: v for k, v in (scope.get("headers") or [])}
    # 1) X-Access-Code header
    if b"x-access-code" in headers:
        return headers[b"x-access-code"].decode("latin-1").strip()
    # 2) ?k= query string
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
    """When AAOS_ACCESS_CODE is non-empty, any /api request without the correct code gets a 401."""

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
