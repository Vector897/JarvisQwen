"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { Skeleton } from "@/components/ui";
import { BarChart, ModelBreakdown } from "@/components/cost-chart";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [costs, setCosts] = useState<any>(null);
  const { subscribe } = useEvents();
  const toast = useToast();

  const load = () => api("/api/dashboard").then(setData).catch(() => {});
  const loadCosts = () => api("/api/dashboard/costs?days=7").then(setCosts).catch(() => {});

  useEffect(() => {
    load();
    loadCosts();
    return subscribe((type, ev) => {
      if (type === "budget_alert") {
        toast(
          `预算${ev.level === "cutoff" ? "已用尽（已熔断）" : "告警"}：$${ev.spent.toFixed(2)} / $${ev.limit}`,
          ev.level === "cutoff" ? "error" : "info"
        );
        load();
      }
      if (["task_done", "task_failed", "briefing_ready"].includes(type)) { load(); loadCosts(); }
    });
  }, [subscribe]);

  if (!data) return <Skeleton rows={4} />;
  const pct = Math.min(100, (data.today_spend_usd / (data.daily_budget_usd || 1)) * 100);
  const cacheRate = data.llm_calls_24h
    ? Math.round((data.cache_hits_24h / data.llm_calls_24h) * 100)
    : 0;

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="mb-1 flex justify-between text-sm">
          <span className="font-medium">今日花费</span>
          <span className="font-mono">${data.today_spend_usd} / ${data.daily_budget_usd}</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
          <div className={`progress-bar ${pct > 80 ? "bg-red-500" : "bg-emerald-500"}`}
            style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-slate-400">
          达 80% 会告警，达 100% 自动熔断挂起任务——不会超支。
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label="运行中任务" value={data.task_counts.RUNNING || 0} href="/tasks" />
        <Stat label="24h LLM 调用" value={data.llm_calls_24h} href="/audit" />
        <Stat label={`24h 缓存命中 (${cacheRate}%)`} value={data.cache_hits_24h} href="/audit" />
        <Stat label="论文总数" value={data.papers_total} href="/library" />
      </div>
      <div className="card text-sm">
        <div className="mb-1 font-medium">任务状态分布</div>
        <div className="text-slate-500">
          {Object.entries(data.task_counts).length
            ? Object.entries(data.task_counts).map(([k, v]) => `${k}: ${v}`).join("　")
            : "暂无任务——去「任务」页下达第一个任务，或在「订阅」页添加自动轮询。"}
        </div>
      </div>

      {costs && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card">
            <div className="mb-2 text-sm font-medium">近 7 天花费趋势</div>
            <BarChart data={costs.daily} />
          </div>
          <div className="card">
            <div className="mb-2 text-sm font-medium">按模型花费占比</div>
            <ModelBreakdown data={costs.by_model} />
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    <Link href={href} className="card-link">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </Link>
  );
}
