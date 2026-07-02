"use client";

import { useEffect, useState } from "react";
import { api, post, subscribeEvents, fmtTime } from "@/lib/api";

export default function Approvals() {
  const [items, setItems] = useState<any[]>([]);
  const load = () => api("/api/approvals").then(setItems).catch(() => {});

  useEffect(() => {
    load();
    const off = subscribeEvents((type) => { if (type === "approval_needed") load(); });
    return off;
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">审批（人类在环）</h1>
      <p className="text-sm text-slate-500">高危操作会在这里等待你批准后从检查点无缝继续。</p>
      {items.map((a) => (
        <div key={a.id} className="card space-y-2">
          <div className="text-sm">{a.action_desc}</div>
          <div className="text-xs text-slate-400">风险等级 {a.risk_level} · {fmtTime(a.created_at)}</div>
          <div className="flex gap-2">
            <button className="btn-primary"
              onClick={() => post(`/api/approvals/${a.id}/approve`, {}).then(load)}>批准</button>
            <button className="btn-ghost text-red-600"
              onClick={() => post(`/api/approvals/${a.id}/reject`, {}).then(load)}>拒绝</button>
          </div>
        </div>
      ))}
      {items.length === 0 && <p className="text-sm text-slate-400">没有待审批项 🎉</p>}
    </div>
  );
}
