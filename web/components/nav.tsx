"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  ["/dashboard", "📊", "仪表盘"],
  ["/tasks", "🔁", "任务"],
  ["/subscriptions", "📡", "订阅"],
  ["/library", "📚", "知识库"],
  ["/briefings", "📰", "简报"],
  ["/approvals", "✅", "审批"],
  ["/audit", "🧾", "审计"],
  ["/settings", "⚙️", "设置"],
] as const;

export default function Nav() {
  const pathname = usePathname();
  if (pathname === "/login") return null;
  return (
    <>
      {/* 桌面端侧栏 */}
      <nav className="hidden md:flex w-52 shrink-0 flex-col gap-1 border-r border-slate-200 bg-white p-4">
        <div className="mb-4 text-lg font-bold">AAOS</div>
        {items.map(([href, icon, label]) => (
          <Link key={href} href={href}
            className={`rounded-lg px-3 py-2 text-sm ${pathname.startsWith(href) ? "bg-slate-900 text-white" : "hover:bg-slate-100"}`}>
            <span className="mr-2">{icon}</span>{label}
          </Link>
        ))}
      </nav>
      {/* 移动端底栏（高频入口） */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex justify-around border-t border-slate-200 bg-white py-2 md:hidden">
        {items.slice(0, 5).map(([href, icon, label]) => (
          <Link key={href} href={href}
            className={`flex flex-col items-center text-xs ${pathname.startsWith(href) ? "text-slate-900 font-bold" : "text-slate-400"}`}>
            <span className="text-lg">{icon}</span>{label}
          </Link>
        ))}
        <Link href="/settings"
          className={`flex flex-col items-center text-xs ${pathname.startsWith("/settings") ? "text-slate-900 font-bold" : "text-slate-400"}`}>
          <span className="text-lg">⚙️</span>设置
        </Link>
      </nav>
    </>
  );
}
