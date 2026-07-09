// SSE-specific streaming reverse proxy: bypasses the buffering that rewrites() in next.config
// applies to streaming responses.
//
// The generic /api/:path* rewrite buffers the SSE response at the proxy layer instead of
// delivering it in real time (manifesting as the frontend only updating state on a manual
// refresh). App Router route handlers take precedence over array-form rewrites (the afterFiles
// stage), so here we handle /api/events separately, passing the backend's ReadableStream
// through as-is; the rest of /api/* still goes through next.config's rewrite.
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const fetchCache = "force-no-store";

const backend = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const upstream = await fetch(`${backend}/api/events`, {
    headers: {
      cookie: req.headers.get("cookie") || "",
      accept: "text/event-stream",
    },
    // Client disconnect → abort the upstream request, triggering the backend's finally: bus.unsubscribe, avoiding subscriber leaks
    signal: req.signal,
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no", // Tell the reverse proxy (nginx) not to buffer either
    },
  });
}
