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
    window.location.href = "/home";
    throw new Error("Not signed in");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

export const post = <T = any>(path: string, body: any) =>
  api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const put = <T = any>(path: string, body: any) =>
  api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const del = <T = any>(path: string) => api<T>(path, { method: "DELETE" });

// SSE 订阅已迁移到全局单连接：见 components/events-provider.tsx 的 useEvents()

export function fmtTime(ts: number): string {
  if (!ts) return "-";
  return new Date(ts * 1000).toLocaleString("zh-CN", { hour12: false });
}

export function fmtEta(ts: number, lang: "zh" | "en" = "en"): string {
  if (!ts) return "";
  const seconds = Math.max(0, ts - Date.now() / 1000);
  if (lang === "zh") {
    if (seconds < 90) return `约 ${Math.ceil(seconds)} 秒后完成`;
    if (seconds < 5400) return `约 ${Math.ceil(seconds / 60)} 分钟后完成`;
    return `预计 ${new Date(ts * 1000).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })} 完成`;
  }
  if (seconds < 90) return `~${Math.ceil(seconds)}s left`;
  if (seconds < 5400) return `~${Math.ceil(seconds / 60)} min left`;
  return `ETA ${new Date(ts * 1000).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

// [中文, English, badge class]
export const STATUS_LABEL: Record<string, [string, string, string]> = {
  QUEUED: ["排队中", "Queued", "bg-slate-200 text-slate-700"],
  RUNNING: ["执行中", "Running", "bg-blue-100 text-blue-700"],
  SUSPENDED: ["已挂起", "Suspended", "bg-amber-100 text-amber-700"],
  WAITING_APPROVAL: ["待审批", "Awaiting approval", "bg-amber-100 text-amber-800"],
  DONE: ["已完成", "Done", "bg-emerald-100 text-emerald-700"],
  FAILED: ["失败", "Failed", "bg-red-100 text-red-700"],
  CANCELLED: ["已取消", "Cancelled", "bg-slate-100 text-slate-500"],
  ZOMBIE: ["已回收", "Reclaimed", "bg-red-50 text-red-500"],
};

export function statusLabel(status: string, lang: "zh" | "en" = "en"): [string, string] {
  const row = STATUS_LABEL[status];
  if (!row) return [status, "bg-slate-100"];
  return [lang === "zh" ? row[0] : row[1], row[2]];
}
