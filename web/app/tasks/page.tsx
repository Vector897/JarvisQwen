"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post, fmtEta, statusLabel } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";
import { useLang } from "@/lib/i18n";

const EXAMPLES = {
  zh: [
    "跟踪 LLM agent security 方向的新论文",
    "调研 reinforcement learning for portfolio optimization 的最新进展",
    "跟踪 diffusion models for protein design",
    "生成今日简报",
  ],
  en: [
    "Track new papers on LLM agent security",
    "Research the latest progress on RL for portfolio optimization",
    "Watch diffusion models for protein design",
    "Generate today's briefing",
  ],
};

export default function Tasks() {
  const [tasks, setTasks] = useState<any[] | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [templates, setTemplates] = useState<any[]>([]);
  const [activeTpl, setActiveTpl] = useState<any>(null);
  const [tplValues, setTplValues] = useState<Record<string, string>>({});
  const { subscribe } = useEvents();
  const toast = useToast();
  const { t, lang } = useLang();

  const load = () => api("/api/tasks").then(setTasks).catch(() => {});

  // Templates carry backend-provided display copy; re-fetch on language change so the picker follows the UI language.
  useEffect(() => {
    api(`/api/tasks/templates?lang=${lang}`).then(setTemplates).catch(() => {});
  }, [lang]);

  useEffect(() => {
    load();
    return subscribe((type, ev) => {
      if (type === "task_progress") {
        setTasks((ts) => (ts || []).map((t) => t.id === ev.task_id
          ? { ...t, progress: ev.progress ?? t.progress, eta_ts: ev.eta_ts ?? t.eta_ts, status: ev.status ?? t.status }
          : t));
      } else if (type === "task_done") { toast(t("tasks.done"), "success"); load(); }
      else if (type === "task_failed") { toast(t("tasks.failed"), "error"); load(); }
      else if (type === "task_suspended") { toast(t("tasks.suspended"), "info"); load(); }
    });
  }, [subscribe]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setBusy(true);
    try {
      const r = await post("/api/tasks", { prompt });
      toast(`${t("tasks.created")}: ${r.title}`, "success");
      setPrompt("");
      load();
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  function openTemplate(tpl: any) {
    setActiveTpl(tpl);
    const initial: Record<string, string> = {};
    for (const f of tpl.fields) initial[f.key] = String(f.default ?? "");
    setTplValues(initial);
  }

  async function submitTemplate(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await post("/api/tasks", { template_id: activeTpl.id, template_values: tplValues });
      toast(`${t("tasks.created")}: ${r.title}`, "success");
      setActiveTpl(null);
      load();
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {templates.map((tpl) => (
          <button key={tpl.id} onClick={() => openTemplate(tpl)}
            className="card-link h-full px-3 py-2 text-left text-xs">
            <div className="font-medium">{tpl.name}</div>
            <div className="mt-0.5 line-clamp-2 text-slate-400">{tpl.description}</div>
          </button>
        ))}
      </div>

      {activeTpl && (
        <form onSubmit={submitTemplate} className="card space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-medium">{activeTpl.name}</div>
            <button type="button" className="text-xs text-slate-400" onClick={() => setActiveTpl(null)}>{t("tasks.templateCancel")}</button>
          </div>
          {activeTpl.fields.map((f: any) => (
            <label key={f.key} className="block text-sm">
              <span className="mb-1 block text-xs text-slate-500">{f.label}</span>
              <input className="input" type={f.type === "number" ? "number" : "text"}
                placeholder={f.placeholder} value={tplValues[f.key] ?? ""}
                onChange={(e) => setTplValues({ ...tplValues, [f.key]: e.target.value })} />
            </label>
          ))}
          <button className="btn-primary" disabled={busy}>{busy ? t("tasks.submitting") : t("tasks.templateSubmit")}</button>
        </form>
      )}

      <form onSubmit={create} className="card space-y-2">
        <textarea className="input" rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder={t("tasks.promptPlaceholder")} />
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? t("tasks.submitting") : t("tasks.submit")}
          </button>
          {EXAMPLES[lang].map((ex) => (
            <button key={ex} type="button" onClick={() => setPrompt(ex)}
              className="rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-500 hover:bg-slate-200">
              {ex.length > 22 ? ex.slice(0, 22) + "…" : ex}
            </button>
          ))}
        </div>
      </form>

      {tasks === null ? (
        <Skeleton rows={3} />
      ) : tasks.length === 0 ? (
        <EmptyState icon="🔁" title={t("tasks.empty")} hint={t("tasks.emptyHint")} />
      ) : (
        <div className="space-y-2">
          {tasks.map((tk) => {
            const [label, cls] = statusLabel(tk.status, lang);
            return (
              <Link key={tk.id} href={`/tasks/${tk.id}`} className="card-link">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{tk.title || tk.type}</div>
                    <div className="text-xs text-slate-400">
                      {tk.type} · ${tk.cost_usd}
                      {tk.status === "RUNNING" && tk.eta_ts ? ` · ${fmtEta(tk.eta_ts, lang)}` : ""}
                    </div>
                  </div>
                  <span className={`badge shrink-0 ${cls}`}>{label}</span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className={`progress-bar ${tk.status === "FAILED" ? "bg-red-400" : "bg-blue-500"}`}
                    style={{ width: `${Math.round((tk.progress || 0) * 100)}%` }} />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
