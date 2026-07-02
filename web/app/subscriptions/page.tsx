"use client";

import { useEffect, useState } from "react";
import { api, post, del, fmtTime } from "@/lib/api";

export default function Subscriptions() {
  const [subs, setSubs] = useState<any[]>([]);
  const [query, setQuery] = useState("");
  const [interval, setInterval_] = useState(360);

  const load = () => api("/api/subscriptions").then(setSubs).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    await post("/api/subscriptions", { query, interval_minutes: interval });
    setQuery("");
    load();
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">订阅（自动轮询）</h1>
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
      <div className="space-y-2">
        {subs.map((s) => (
          <div key={s.id} className="card flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="truncate font-medium">{s.query}</div>
              <div className="text-xs text-slate-400">
                每 {s.interval_minutes} 分钟 · 上次运行 {fmtTime(s.last_run_at)}
              </div>
            </div>
            <div className="flex shrink-0 gap-2">
              <button className="btn-ghost text-xs"
                onClick={() => post(`/api/subscriptions/${s.id}/toggle`, {}).then(load)}>
                {s.enabled ? "暂停" : "启用"}
              </button>
              <button className="btn-ghost text-xs text-red-600"
                onClick={() => del(`/api/subscriptions/${s.id}`).then(load)}>删除</button>
            </div>
          </div>
        ))}
        {subs.length === 0 && <p className="text-sm text-slate-400">暂无订阅。添加后系统将 7×24 自动轮询、归档并总结新论文。</p>}
      </div>
    </div>
  );
}
