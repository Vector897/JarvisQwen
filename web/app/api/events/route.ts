// SSE 专用流式反代：绕过 next.config 里 rewrites() 对流式响应的缓冲。
//
// 通用的 /api/:path* rewrite 会把 SSE 响应攒在代理层不实时下发（表现为
// 前端只有手动刷新才更新状态）。App Router 的路由处理器优先级高于数组形式
// 的 rewrite（afterFiles 阶段），因此这里单独接管 /api/events，把后端的
// ReadableStream 原样透传；其余 /api/* 仍走 next.config 的 rewrite。
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
    // 客户端断开 → 中止上游请求，触发后端 finally: bus.unsubscribe，避免订阅者泄漏
    signal: req.signal,
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no", // 反代（nginx）也不缓冲
    },
  });
}
