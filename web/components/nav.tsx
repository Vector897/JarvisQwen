"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLang } from "@/lib/i18n";

const items = [
  ["/dashboard", "📊", "nav.dashboard"],
  ["/tasks", "🔁", "nav.tasks"],
  ["/subscriptions", "📡", "nav.subscriptions"],
  ["/library", "📚", "nav.library"],
  ["/briefings", "📰", "nav.briefings"],
  ["/approvals", "✅", "nav.approvals"],
  ["/audit", "🧾", "nav.audit"],
  ["/connect", "📱", "nav.connect"],
  ["/deploy", "🚀", "nav.deploy"],
  ["/settings", "⚙️", "nav.settings"],
  ["/help", "❓", "nav.help"],
] as const;

export default function Nav() {
  const pathname = usePathname();
  const { t } = useLang();
  if (pathname === "/login" || pathname === "/home") return null;
  return (
    <>
      {/* 桌面端侧栏 */}
      <nav className="hidden md:flex w-52 shrink-0 flex-col gap-1 border-r border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
        <Link href="/home" className="mb-4 flex items-center gap-2 text-lg font-bold">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo-icon.png" alt="JarvisQwen logo" className="h-8 w-8 rounded-lg" />
          JarvisQwen
        </Link>
        {items.map(([href, icon, key]) => (
          <Link key={href} href={href}
            className={`rounded-lg px-3 py-2 text-sm transition-colors ${pathname.startsWith(href) ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900" : "hover:bg-slate-100 dark:hover:bg-slate-800"}`}>
            <span className="mr-2">{icon}</span>{t(key)}
          </Link>
        ))}
      </nav>
      {/* 移动端底栏（高频入口） */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex justify-around border-t border-slate-200 bg-white py-2 dark:border-slate-800 dark:bg-slate-900 md:hidden">
        {items.slice(0, 4).map(([href, icon, key]) => (
          <Link key={href} href={href}
            className={`flex flex-col items-center text-xs ${pathname.startsWith(href) ? "text-slate-900 dark:text-white font-bold" : "text-slate-400"}`}>
            <span className="text-lg">{icon}</span>{t(key)}
          </Link>
        ))}
        <Link href="/help"
          className={`flex flex-col items-center text-xs ${pathname.startsWith("/help") ? "text-slate-900 dark:text-white font-bold" : "text-slate-400"}`}>
          <span className="text-lg">❓</span>{t("nav.help")}
        </Link>
      </nav>
    </>
  );
}
