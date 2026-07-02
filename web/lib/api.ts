"use client";

export async function api<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (res.status === 401 && typeof window !== "undefined" && !path.includes("/auth/")) {
    window.location.href = "/login";
    throw new Error("未登录");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `请求失败 (${res.status})`);
  }
  return res.json();
}

export const post = <T = any>(path: string, body: any) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T = any>(path: string, body: any) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const del = <T = any>(path: string) => api<T>(path, { method: "DELETE" });

/** 订阅 SSE 事件流；返回取消函数。 */
export function subscribeEvents(onEvent: (type: string, data: any) => void): () => void {
  const es = new EventSource("/api/events");
  const types = [
    "task_progress", "task_done", "task_failed", "task_suspended",
    "budget_alert", "briefing_ready", "approval_needed", "task_zombie_requeued",
  ];
  for (const t of types) {
    es.addEventListener(t, (e) => onEvent(t, JSON.parse((e as MessageEvent).data)));
  }
  return () => es.close();
}

export function fmtTime(ts: number): string {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString("zh-CN", { hour12: false });
}

export function fmtEta(ts: number): string {
  if (!ts) return "";
  const seconds = Math.max(0, ts - Date.now() / 1000);
  if (seconds < 90) return `约 ${Math.ceil(seconds)} 秒后完成`;
  if (seconds < 5400) return `约 ${Math.ceil(seconds / 60)} 分钟后完成`;
  return `预计 ${new Date(ts * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })} 完成`;
}

export const STATUS_LABEL: Record<string, [string, string]> = {
  QUEUED: ["排队中", "bg-slate-200 text-slate-700"],
  RUNNING: ["执行中", "bg-blue-100 text-blue-700"],
  SUSPENDED: ["已挂起", "bg-amber-100 text-amber-700"],
  WAITING_APPROVAL: ["待审批", "bg-amber-100 text-amber-800"],
  DONE: ["已完成", "bg-emerald-100 text-emerald-700"],
  FAILED: ["失败", "bg-red-100 text-red-700"],
  CANCELLED: ["已取消", "bg-slate-100 text-slate-500"],
  ZOMBIE: ["已回收", "bg-red-50 text-red-500"],
};
