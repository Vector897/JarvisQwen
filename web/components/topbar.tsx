"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, post } from "@/lib/api";
import { useEvents } from "./events-provider";
import { useTheme } from "./theme-provider";
import { useLang } from "@/lib/i18n";

const TITLES: Record<string, [string, string]> = {
  "/dashboard": ["仪表盘", "Dashboard"], "/tasks": ["任务", "Tasks"],
  "/subscriptions": ["订阅", "Subscriptions"], "/library": ["知识库", "Library"],
  "/briefings": ["简报", "Briefings"], "/approvals": ["审批", "Approvals"],
  "/audit": ["审计", "Audit"], "/settings": ["设置", "Settings"], "/help": ["帮助", "Help"],
};

const DOT: Record<string, [string, string]> = {
  online: ["bg-emerald-500", "topbar.online"],
  offline: ["bg-red-500", "topbar.offline"],
  connecting: ["bg-amber-400", "topbar.offline"],
};

export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useEvents();
  const { theme, toggle: toggleTheme } = useTheme();
  const { lang, t, toggle: toggleLang } = useLang();
  const [user, setUser] = useState<{ name: string; role: string } | null>(null);

  useEffect(() => {
    if (pathname === "/login") return;
    api("/api/auth/me").then(setUser).catch(() => {});
  }, [pathname]);

  if (pathname === "/login") return null;
  const titlePair = Object.entries(TITLES).find(([p]) => pathname.startsWith(p))?.[1];
  const title = titlePair ? (lang === "zh" ? titlePair[0] : titlePair[1]) : "AAOS";
  const [dotCls, dotKey] = DOT[status] as [string, "topbar.online" | "topbar.offline"];

  async function logout() {
    await post("/api/auth/logout", {}).catch(() => {});
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-slate-200 bg-white/90 px-4 py-2.5 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90 md:px-8">
      <h2 className="text-base font-semibold md:text-lg">{title}</h2>
      <div className="flex items-center gap-1.5 text-xs text-slate-400" title={t(dotKey)}>
        <span className={`inline-block h-2 w-2 rounded-full ${dotCls} ${status === "online" ? "" : "animate-pulse"}`} />
        <span className="hidden sm:inline">{t(dotKey)}</span>
      </div>
      <div className="ml-auto flex items-center gap-2">
        <button onClick={toggleTheme} className="btn-ghost text-xs" title="切换深色/浅色">
          {theme === "dark" ? "☀️" : "🌙"}
        </button>
        <button onClick={toggleLang} className="btn-ghost text-xs" title="切换语言 / Switch language">
          {lang === "zh" ? "EN" : "中"}
        </button>
        {user && (
          <span className="hidden text-xs text-slate-500 sm:inline">
            {user.name}{user.role === "admin" ? ` (${t("topbar.admin")})` : ""}
          </span>
        )}
        <button onClick={logout} className="btn-ghost text-xs">{t("topbar.logout")}</button>
      </div>
    </header>
  );
}
