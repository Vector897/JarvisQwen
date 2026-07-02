"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post, subscribeEvents, fmtEta, STATUS_LABEL } from "@/lib/api";

export default function Tasks() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [prompt, setPrompt] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => api("/api/tasks").then(setTasks).catch(() => {});

  useEffect(() => {
    load();
    const off = subscribeEvents((type, ev) => {
      if (type === "task_progress") {
        setTasks((ts) => ts.map((t) => t.id === ev.task_id
          ? { ...t, progress: ev.progress ?? t.progress, eta_ts: ev.eta_ts ?? t.eta_ts, status: ev.status ?? t.status }
          : t));
      } else if (["task_done", "task_failed", "task_suspended"].includes(type)) load();
    });
    return off;
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    try {
      const r = await post("/api/tasks", { prompt });
      setMsg(`已创建任务「${r.title}」`);
      setPrompt("");
      load();
    } catch (err: any) {
      setMsg(err.message);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">任务</h1>
      <form onSubmit={create} className="card flex flex-col gap-2 md:flex-row">
        <input className="input flex-1" value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder='用自然语言下任务，如："帮我调研 catastrophic forgetting in CFR 的最新进展"' />
        <button className="btn-primary justify-center" type="submit">提交任务</button>
      </form>
      {msg && <p className="text-sm text-slate-500">{msg}</p>}
      <div className="space-y-2">
        {tasks.map((t) => {
          const [label, cls] = STATUS_LABEL[t.status] || [t.status, "bg-slate-100"];
          return (
            <Link key={t.id} href={`/tasks/${t.id}`} className="card block hover:border-slate-400">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="truncate font-medium">{t.title || t.type}</div>
                  <div className="text-xs text-slate-400">
                    {t.type} · ${t.cost_usd}
                    {t.status === "RUNNING" && t.eta_ts ? ` · ${fmtEta(t.eta_ts)}` : ""}
                  </div>
                </div>
                <span className={`badge shrink-0 ${cls}`}>{label}</span>
              </div>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div className={`h-full transition-all ${t.status === "FAILED" ? "bg-red-400" : "bg-blue-500"}`}
                  style={{ width: `${Math.round((t.progress || 0) * 100)}%` }} />
              </div>
            </Link>
          );
        })}
        {tasks.length === 0 && <p className="text-sm text-slate-400">还没有任务，在上面输入框下达第一个任务吧。</p>}
      </div>
    </div>
  );
}
