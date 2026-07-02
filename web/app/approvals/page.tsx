"use client";

import { useEffect, useState } from "react";
import { api, post, fmtTime } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";

export default function Approvals() {
  const [items, setItems] = useState<any[] | null>(null);
  const { subscribe } = useEvents();
  const toast = useToast();

  const load = () => api("/api/approvals").then(setItems).catch(() => {});

  useEffect(() => {
    load();
    return subscribe((type) => {
      if (type === "approval_needed") { toast("有新的待审批操作", "info"); load(); }
    });
  }, [subscribe]);

  async function decide(id: string, action: "approve" | "reject") {
    await post(`/api/approvals/${id}/${action}`, {});
    toast(action === "approve" ? "已批准，任务将从检查点继续" : "已拒绝", action === "approve" ? "success" : "info");
    load();
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">高危操作会在这里等待你批准后从检查点无缝继续。</p>
      {items === null ? (
        <Skeleton rows={2} />
      ) : items.length === 0 ? (
        <EmptyState icon="✅" title="没有待审批项" hint="当任务触发高危操作（如对外发送、删除）时会出现在这里。" />
      ) : (
        items.map((a) => (
          <div key={a.id} className="card space-y-2">
            <div className="text-sm">{a.action_desc}</div>
            <div className="text-xs text-slate-400">风险等级 {a.risk_level} · {fmtTime(a.created_at)}</div>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={() => decide(a.id, "approve")}>批准</button>
              <button className="btn-ghost text-red-600" onClick={() => decide(a.id, "reject")}>拒绝</button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
