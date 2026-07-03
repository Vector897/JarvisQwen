"use client";

import { useEffect, useState } from "react";
import { api, post, del, fmtTime } from "@/lib/api";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";
import { useLang } from "@/lib/i18n";

export default function Subscriptions() {
  const [subs, setSubs] = useState<any[] | null>(null);
  const [query, setQuery] = useState("");
  const [interval, setInterval_] = useState(360);
  const toast = useToast();
  const { t, lang } = useLang();

  const load = () => api("/api/subscriptions").then(setSubs).catch(() => {});
  useEffect(() => { load(); }, []);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    await post("/api/subscriptions", { query, interval_minutes: interval });
    toast(`${t("subs.added")}「${query}」`, "success");
    setQuery("");
    load();
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">{t("subs.hint")}</p>
      <form onSubmit={add} className="card flex flex-col gap-2 md:flex-row">
        <input className="input flex-1" value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={t("subs.queryPlaceholder")} />
        <select className="input md:w-44" value={interval}
          onChange={(e) => setInterval_(Number(e.target.value))}>
          <option value={60}>{t("subs.every1h")}</option>
          <option value={360}>{t("subs.every6h")}</option>
          <option value={720}>{t("subs.every12h")}</option>
          <option value={1440}>{t("subs.everyDay")}</option>
        </select>
        <button className="btn-primary justify-center">{t("subs.add")}</button>
      </form>
      {subs === null ? (
        <Skeleton rows={2} />
      ) : subs.length === 0 ? (
        <EmptyState icon="📡" title={t("subs.empty")} hint={t("subs.emptyHint")} />
      ) : (
        <div className="space-y-2">
          {subs.map((s) => (
            <div key={s.id} className="card flex items-center justify-between gap-2">
              <div className="min-w-0">
                <div className="truncate font-medium">{s.query}</div>
                <div className="text-xs text-slate-400">
                  {lang === "zh" ? `每 ${s.interval_minutes} 分钟` : `every ${s.interval_minutes} min`}
                  {" · "}{fmtTime(s.last_run_at)}
                  {!s.enabled && ` · ${t("subs.paused")}`}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <button className="btn-ghost text-xs"
                  onClick={() => post(`/api/subscriptions/${s.id}/toggle`, {}).then(() => { toast(s.enabled ? t("subs.paused") : t("subs.enable"), "info"); load(); })}>
                  {s.enabled ? t("subs.pause") : t("subs.enable")}
                </button>
                <button className="btn-ghost text-xs text-red-600"
                  onClick={() => del(`/api/subscriptions/${s.id}`).then(() => { toast(t("subs.delete"), "info"); load(); })}>
                  {t("subs.delete")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
