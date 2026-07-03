"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { Skeleton } from "@/components/ui";
import { BarChart, ModelBreakdown } from "@/components/cost-chart";
import { useLang } from "@/lib/i18n";

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [costs, setCosts] = useState<any>(null);
  const { subscribe } = useEvents();
  const toast = useToast();
  const { t } = useLang();

  const load = () => api("/api/dashboard").then(setData).catch(() => {});
  const loadCosts = () => api("/api/dashboard/costs?days=7").then(setCosts).catch(() => {});

  useEffect(() => {
    load();
    loadCosts();
    return subscribe((type, ev) => {
      if (type === "budget_alert") {
        toast(
          `${ev.level === "cutoff" ? t("dashboard.budgetCutoff") : t("dashboard.budgetWarn")}：$${ev.spent.toFixed(2)} / $${ev.limit}`,
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
          <span className="font-medium">{t("dashboard.spendToday")}</span>
          <span className="font-mono">${data.today_spend_usd} / ${data.daily_budget_usd}</span>
        </div>
        <div className="h-3 w-full overflow-hidden rounded-full bg-slate-100">
          <div className={`progress-bar ${pct > 80 ? "bg-red-500" : "bg-emerald-500"}`}
            style={{ width: `${pct}%` }} />
        </div>
        <p className="mt-1 text-xs text-slate-400">{t("dashboard.budgetHint")}</p>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <Stat label={t("dashboard.runningTasks")} value={data.task_counts.RUNNING || 0} href="/tasks" />
        <Stat label={t("dashboard.calls24h")} value={data.llm_calls_24h} href="/audit" />
        <Stat label={`${t("dashboard.cacheHits24h")} (${cacheRate}%)`} value={data.cache_hits_24h} href="/audit" />
        <Stat label={t("dashboard.papersTotal")} value={data.papers_total} href="/library" />
      </div>
      <div className="card text-sm">
        <div className="mb-1 font-medium">{t("dashboard.statusBreakdown")}</div>
        <div className="text-slate-500">
          {Object.entries(data.task_counts).length
            ? Object.entries(data.task_counts).map(([k, v]) => `${k}: ${v}`).join("　")
            : t("dashboard.noTasks")}
        </div>
      </div>

      {costs && (
        <div className="grid gap-4 md:grid-cols-2">
          <div className="card">
            <div className="mb-2 text-sm font-medium">{t("dashboard.costTrend")}</div>
            <BarChart data={costs.daily} />
          </div>
          <div className="card">
            <div className="mb-2 text-sm font-medium">{t("dashboard.costByModel")}</div>
            <ModelBreakdown data={costs.by_model} />
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    // @container：数字大小按卡片自身可用宽度（cqi）流体缩放，而非全局视口断点——
    // 同一个 Stat 组件放进 2 列或 4 列布局都会自适应，不需要写死 text-2xl/text-lg 断点判断。
    <Link href={href} className="card-link @container">
      <div className="font-bold" style={{ fontSize: "clamp(1.25rem, 12cqi, 1.75rem)" }}>{value}</div>
      <div className="text-xs text-content-muted">{label}</div>
    </Link>
  );
}
