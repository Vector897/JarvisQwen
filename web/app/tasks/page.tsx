"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, post, fmtEta, STATUS_LABEL } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";

const EXAMPLES = [
  "帮我调研 catastrophic forgetting in counterfactual regret minimization 的最新进展",
  "跟踪 multi-agent debate 方向的新论文",
  "生成今日简报",
];

export default function Tasks() {
  const [tasks, setTasks] = useState<any[] | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const { subscribe } = useEvents();
  const toast = useToast();

  const load = () => api("/api/tasks").then(setTasks).catch(() => {});

  useEffect(() => {
    load();
    return subscribe((type, ev) => {
      if (type === "task_progress") {
        setTasks((ts) => (ts || []).map((t) => t.id === ev.task_id
          ? { ...t, progress: ev.progress ?? t.progress, eta_ts: ev.eta_ts ?? t.eta_ts, status: ev.status ?? t.status }
          : t));
      } else if (type === "task_done") { toast("任务完成", "success"); load(); }
      else if (type === "task_failed") { toast("任务失败，可从检查点重跑", "error"); load(); }
      else if (type === "task_suspended") { toast("任务已挂起（预算或等待）", "info"); load(); }
    });
  }, [subscribe]);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setBusy(true);
    try {
      const r = await post("/api/tasks", { prompt });
      toast(`已创建任务「${r.title}」`, "success");
      setPrompt("");
      load();
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <form onSubmit={create} className="card space-y-2">
        <textarea className="input" rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder='用自然语言下任务，如："帮我调研 XXX 的最新进展"' />
        <div className="flex flex-wrap items-center gap-2">
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "提交中…" : "提交任务"}
          </button>
          {EXAMPLES.map((ex) => (
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
        <EmptyState icon="🔁" title="还没有任务"
          hint="在上面输入框用自然语言下达第一个任务，或点一个示例快速填入。" />
      ) : (
        <div className="space-y-2">
          {tasks.map((t) => {
            const [label, cls] = STATUS_LABEL[t.status] || [t.status, "bg-slate-100"];
            return (
              <Link key={t.id} href={`/tasks/${t.id}`} className="card-link">
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
                  <div className={`progress-bar ${t.status === "FAILED" ? "bg-red-400" : "bg-blue-500"}`}
                    style={{ width: `${Math.round((t.progress || 0) * 100)}%` }} />
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
