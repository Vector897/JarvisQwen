"use client";

import { useEffect, useState } from "react";
import { api, post, fmtTime } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";
import { useLang } from "@/lib/i18n";

export default function Approvals() {
  const [items, setItems] = useState<any[] | null>(null);
  const { subscribe } = useEvents();
  const toast = useToast();
  const { t } = useLang();

  const load = () => api("/api/approvals").then(setItems).catch(() => {});

  useEffect(() => {
    load();
    return subscribe((type) => {
      if (type === "approval_needed") { toast(t("approvals.newOne"), "info"); load(); }
    });
  }, [subscribe]);

  async function decide(id: string, action: "approve" | "reject") {
    await post(`/api/approvals/${id}/${action}`, {});
    toast(action === "approve" ? t("approvals.approved") : t("approvals.rejected"), action === "approve" ? "success" : "info");
    load();
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">{t("approvals.hint")}</p>
      {items === null ? (
        <Skeleton rows={2} />
      ) : items.length === 0 ? (
        <EmptyState icon="✅" title={t("approvals.empty")} hint={t("approvals.emptyHint")} />
      ) : (
        items.map((a) => (
          <div key={a.id} className="card space-y-2">
            <div className="text-sm">{a.action_desc}</div>
            <div className="text-xs text-slate-400">{t("approvals.riskLevel")} {a.risk_level} · {fmtTime(a.created_at)}</div>
            <div className="flex gap-2">
              <button className="btn-primary" onClick={() => decide(a.id, "approve")}>{t("approvals.approve")}</button>
              <button className="btn-ghost text-red-600" onClick={() => decide(a.id, "reject")}>{t("approvals.reject")}</button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
