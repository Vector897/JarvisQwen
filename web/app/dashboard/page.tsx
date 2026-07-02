"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, subscribeEvents } from "@/lib/api";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [alerts, setAlerts] = useState<string[]>([]);

  const load = () => api("/api/dashboard").then(setData).catch(() => {});

  useEffect(() => {
    load();
    const off = subscribeEvents((type, ev) => {
      if (type === "budget_alert")
        setAlerts((a) => [`预算告警：已花费 $${ev.spent.toFixed(2)} / $${ev.limit}`, ...a.slice(0, 4)]);
      if (["task_done", "task_failed", "briefing_ready"].includes(type)) load();
    });
    return off;
  }, []);

  if (!data) return <p className="text-slate-400">加载中…</p>;
  const pct = Math.min(100, (data.today_spend_usd / (data.daily_budget_usd || 1)) * 100);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">仪表盘</h1>
      {alerts.map((a, i) => (
        <div key={i} className="card border-amber-300 bg-amber-50 text-sm text-amber-800">{a}</div>
      ))}
      <div className="card">
        <div className="mb-1 flex justify-between text-sm">
          <span>今日花费</span>
          <span className="font-mono">${data.today_spend_usd} / ${data.daily_budget_usd}</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
          <div className={`h-full ${pct > 80 ? "bg-red-500" : "bg-emerald-500"}`}
            style={{ width: `${pct}%` }} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="运行中任务" value={data.task_counts.RUNNING || 0} href="/tasks" />
        <Stat label="24h LLM 调用" value={data.llm_calls_24h} href="/audit" />
        <Stat label="24h 缓存命中" value={data.cache_hits_24h} href="/audit" />
        <Stat label="论文总数" value={data.papers_total} href="/library" />
      </div>
      <div className="card text-sm text-slate-500">
        任务状态：{Object.entries(data.task_counts).map(([k, v]) => `${k}:${v}`).join("  ") || "暂无任务"}
      </div>
    </div>
  );
}

function Stat({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <Link href={href} className="card block hover:border-slate-400">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </Link>
  );
}
