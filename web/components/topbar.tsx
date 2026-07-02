"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { api, post } from "@/lib/api";
import { useEvents } from "./events-provider";

const TITLES: Record<string, string> = {
  "/dashboard": "仪表盘", "/tasks": "任务", "/subscriptions": "订阅",
  "/library": "知识库", "/briefings": "简报", "/approvals": "审批",
  "/audit": "审计", "/settings": "设置", "/help": "帮助",
};

const DOT: Record<string, [string, string]> = {
  online: ["bg-emerald-500", "实时连接正常"],
  offline: ["bg-red-500", "连接断开，重连中…"],
  connecting: ["bg-amber-400", "连接中…"],
};

export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useEvents();
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);

  useEffect(() => {
    if (pathname === "/login") return;
    api("/api/auth/me").then(setUser).catch(() => {});
  }, [pathname]);

  if (pathname === "/login") return null;
  const title = Object.entries(TITLES).find(([p]) => pathname.startsWith(p))?.[1] || "AAOS";
  const [dotCls, dotLabel] = DOT[status];

  async function logout() {
    await post("/api/auth/logout", {}).catch(() => {});
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur md:px-8">
      <h2 className="text-base font-semibold md:text-lg">{title}</h2>
      <div className="flex items-center gap-1.5 text-xs text-slate-400" title={dotLabel}>
        <span className={`inline-block h-2 w-2 rounded-full ${dotCls} ${status === "online" ? "" : "animate-pulse"}`} />
        <span className="hidden sm:inline">{dotLabel}</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <Link href="/help" className="btn-ghost text-xs" title="使用帮助">? 帮助</Link>
        {user && (
          <span className="hidden text-xs text-slate-500 sm:inline">
            {user.name}{user.role === "admin" ? "（管理员）" : ""}
          </span>
        )}
        <button onClick={logout} className="btn-ghost text-xs">登出</button>
      </div>
    </header>
  );
}
