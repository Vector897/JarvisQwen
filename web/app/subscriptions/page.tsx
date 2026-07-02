"use client";

import { useEffect, useState } from "react";
import { api, post, del, fmtTime } from "@/lib/api";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";

export default function Subscriptions() {
  const [subs, setSubs] = useState<any[] | null>(null);
  const [query, setQuery] = useState("");
  const [interval, setInterval_] = useState(360);
  const toast = useToast();

  const load = () => api("/api/subscriptions").then(setSubs).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    await post("/api/subscriptions", { query, interval_minutes: interval });
    toast(`已添加订阅「${query}」`, "success");
    setQuery("");
    load();
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">
        添加后系统 7×24 自动轮询 arXiv、去重、初筛、归档并总结新论文——你的电脑可以关机。
      </p>
      <form onSubmit={add} className="card flex flex-col gap-2 md:flex-row">
        <input className="input flex-1" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder="arXiv 关键词，如：counterfactual regret minimization" />
        <select className="input md:w-44" value={interval}
          onChange={(e) => setInterval_(Number(e.target.value))}>
          <option value={60}>每 1 小时</option>
          <option value={360}>每 6 小时</option>
          <option value={720}>每 12 小时</option>
          <option value={1440}>每天</option>
        </select>
        <button className="btn-primary justify-center">添加订阅</button>
      </form>
      {subs === null ? (
        <Skeleton rows={2} />
      ) : subs.length === 0 ? (
        <EmptyState icon="📡" title="还没有订阅" hint="添加一个研究关键词，系统就会自动帮你盯着新论文。" />
      ) : (
        <div className="space-y-2">
          {subs.map((s) => (
            <div key={s.id} className="card flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate font-medium">{s.query}</div>
                <div className="text-xs text-slate-400">
                  每 {s.interval_minutes} 分钟 · 上次运行 {fmtTime(s.last_run_at)}
                  {!s.enabled && " · 已暂停"}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button className="btn-ghost text-xs"
                  onClick={() => post(`/api/subscriptions/${s.id}/toggle`, {}).then(() => { toast(s.enabled ? "已暂停" : "已启用", "info"); load(); })}>
                  {s.enabled ? "暂停" : "启用"}
                </button>
                <button className="btn-ghost text-xs text-red-600"
                  onClick={() => del(`/api/subscriptions/${s.id}`).then(() => { toast("已删除订阅", "info"); load(); })}>删除</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
