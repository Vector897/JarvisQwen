"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { Skeleton } from "@/components/ui";
import { BarChart, ModelBreakdown } from "@/components/cost-chart";
import { useLang } from "@/lib/i18n";

const TIERS = [
  ["Rule tier", "— pure code", "$0", ["Poll · dedupe · archive · notify", "轮询 · 去重 · 归档 · 推送"]],
  ["Light tier", "qwen3.6-flash", "$0.25 / $1.50", ["Triage · briefings · NLU", "初筛 · 简报 · 指令解析"]],
  ["Fallback", "qwen3.7-plus", "$0.40 / $1.60", ["Resilience chain", "弹性降级链"]],
  ["Frontier", "qwen3.7-max", "$2.50 / $7.50", ["Deep summaries only", "仅深度总结"]],
] as const;

export default function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [costs, setCosts] = useState<any>(null);
  const [calls, setCalls] = useState<any[]>([]);
  const { subscribe } = useEvents();
  const toast = useToast();
  const { t, lang } = useLang();

  const load = () => api("/api/dashboard").then(setData).catch(() => {});
  const loadCosts = () => api("/api/dashboard/costs?days=7").then(setCosts).catch(() => {});
  const loadCalls = () => api("/api/audit?limit=6").then(setCalls).catch(() => {});

  useEffect(() => {
    load();
    loadCosts();
    loadCalls();
    return subscribe((type, ev) => {
      if (type === "budget_alert") {
        toast(
          `${ev.level === "cutoff" ? t("dashboard.budgetCutoff") : t("dashboard.budgetWarn")}：$${ev.spent.toFixed(2)} / $${ev.limit}`,
          ev.level === "cutoff" ? "error" : "info"
        );
        load();
      }
      if (["task_done", "task_failed", "briefing_ready"].includes(type)) { load(); loadCosts(); loadCalls(); }
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

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recent LLM calls */}
        <div className="card overflow-x-auto">
          <div className="mb-2 flex items-center justify-between text-sm">
            <span className="font-medium">{lang === "zh" ? "最近 LLM 调用" : "Recent LLM calls"}</span>
            <Link href="/audit" className="text-xs text-blue-600 hover:underline">
              {lang === "zh" ? "完整审计 →" : "Full audit →"}
            </Link>
          </div>
          {calls.length ? (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-400 dark:border-slate-700">
                  <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "时间" : "Time"}</th>
                  <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "模型" : "Model"}</th>
                  <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "步骤" : "Step"}</th>
                  <th className="py-1.5 pr-2 text-right font-medium">Tokens</th>
                  <th className="py-1.5 text-right font-medium">{lang === "zh" ? "费用" : "Cost"}</th>
                </tr>
              </thead>
              <tbody>
                {calls.map((c) => (
                  <tr key={c.id} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                    <td className="py-1.5 pr-2 text-slate-400">
                      {new Date(c.ts * 1000).toLocaleTimeString(lang === "zh" ? "zh-CN" : "en-GB",
                        { hour: "2-digit", minute: "2-digit" })}
                    </td>
                    <td className="py-1.5 pr-2 font-mono">{c.model.replace("qwen/", "")}</td>
                    <td className="py-1.5 pr-2 text-slate-500">{c.step}</td>
                    <td className="py-1.5 pr-2 text-right font-mono text-slate-500">{c.tokens_in}→{c.tokens_out}</td>
                    <td className="py-1.5 text-right font-mono">${c.cost_usd.toFixed(4)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-xs text-slate-400">{lang === "zh" ? "暂无调用记录" : "No calls yet"}</p>
          )}
        </div>

        {/* Qwen three-tier routing price list */}
        <div className="card overflow-x-auto">
          <div className="mb-2 text-sm font-medium">
            {lang === "zh" ? "三级路由 · Qwen 全家桶价目" : "Tiered routing · the Qwen family"}
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 text-left text-slate-400 dark:border-slate-700">
                <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "层级" : "Tier"}</th>
                <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "模型" : "Model"}</th>
                <th className="py-1.5 pr-2 font-medium">{lang === "zh" ? "单价 /MTok" : "Price /MTok"}</th>
                <th className="py-1.5 font-medium">{lang === "zh" ? "职责" : "Handles"}</th>
              </tr>
            </thead>
            <tbody>
              {TIERS.map(([tier, model, price, duty]) => (
                <tr key={tier} className="border-b border-slate-100 last:border-0 dark:border-slate-800">
                  <td className="py-1.5 pr-2 font-medium">{tier}</td>
                  <td className="py-1.5 pr-2 font-mono">{model}</td>
                  <td className="py-1.5 pr-2 font-mono">{price}</td>
                  <td className="py-1.5 text-slate-500">{lang === "zh" ? duty[1] : duty[0]}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-400">
            {lang === "zh"
              ? "每个 token 都花在能干这活的最便宜模型上——这是 ~$0.30/天 的由来。"
              : "Every token goes to the cheapest model that can do the job — that's how ~$0.30/day happens."}
          </p>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, href }: { label: string; value: number; href: string }) {
  return (
    // @container: the number size scales fluidly against the card's own available width (cqi)
    // rather than global viewport breakpoints — so the same Stat component adapts whether it sits
    // in a 2-column or 4-column layout, with no hard-coded text-2xl/text-lg breakpoint logic.
    <Link href={href} className="card-link @container">
      <div className="font-bold" style={{ fontSize: "clamp(1.25rem, 12cqi, 1.75rem)" }}>{value}</div>
      <div className="text-xs text-content-muted">{label}</div>
    </Link>
  );
}
