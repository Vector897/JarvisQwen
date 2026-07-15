"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ReactFlow, Background, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, post, fmtEta, fmtTime, statusLabel } from "@/lib/api";
import { useEvents } from "@/components/events-provider";
import { useToast } from "@/components/toast";
import { Skeleton } from "@/components/ui";
import { useLang } from "@/lib/i18n";

const NODE_COLOR: Record<string, string> = {
  done: "#10b981",
  running: "#3b82f6",
  waiting_approval: "#f59e0b",
  suspended: "#f59e0b",
  failed: "#ef4444",
  pending: "#cbd5e1",
};

export default function TaskDetail() {
  const { id } = useParams<{ id: string }>();
  const [task, setTask] = useState<any>(null);
  const [sub, setSub] = useState("");
  const { subscribe } = useEvents();
  const toast = useToast();
  const { t, lang } = useLang();
  const L = (en: string, zh: string) => (lang === "zh" ? zh : en);

  const load = useCallback(() => api(`/api/tasks/${id}`).then(setTask).catch(() => {}), [id]);

  useEffect(() => {
    load();
    return subscribe((type, ev) => {
      if (ev.task_id !== id) return;
      if (ev.sub_progress) setSub(ev.sub_progress);
      load();
    });
  }, [id, load, subscribe]);

  if (!task) return <Skeleton rows={4} />;
  const [label, cls] = statusLabel(task.status, lang);

  const scrollToEl = (elId: string) =>
    document.getElementById(elId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  // Click a pipeline node to jump straight to that step's artifact — expand it, then scroll.
  const onNodeClick = (_: unknown, node: Node) => {
    const step = task.pipeline[Number(node.id)]?.name;
    const idx = task.artifacts.findIndex((a: any) => a.step === step);
    if (idx >= 0) {
      const el = document.getElementById(`artifact-${idx}`) as HTMLDetailsElement | null;
      if (el) {
        el.open = true;
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        return;
      }
    }
    scrollToEl("artifacts");
  };

  const nodes: Node[] = task.pipeline.map((s: any, i: number) => ({
    id: String(i),
    position: { x: i * 170, y: 40 },
    data: { label: `${s.name}\n(~${s.est_duration}s)` },
    style: {
      background: "#fff",
      border: `3px solid ${NODE_COLOR[s.status] || "#cbd5e1"}`,
      borderRadius: 12,
      fontSize: 12,
      whiteSpace: "pre-line",
      width: 140,
      textAlign: "center" as const,
      cursor: "pointer",
    },
  }));
  const edges: Edge[] = task.pipeline.slice(1).map((_: any, i: number) => ({
    id: `e${i}`, source: String(i), target: String(i + 1), animated: task.status === "RUNNING",
  }));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold">{task.title || task.type}</h1>
        <span className={`badge ${cls}`}>{label}</span>
      </div>

      <div className="card">
        <div className="mb-1 flex flex-wrap justify-between text-sm">
          <span>{t("taskDetail.totalProgress")} {Math.round((task.progress || 0) * 100)}%{sub ? ` · ${sub}` : ""}</span>
          <span className="text-slate-500">
            {task.status === "RUNNING" && task.eta_ts ? fmtEta(task.eta_ts, lang) : ""}
            {task.status === "DONE" ? `${t("taskDetail.finishedAt")} ${fmtTime(task.finished_at)}` : ""}
          </span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full bg-blue-500 transition-all duration-700 ease-out"
            style={{ width: `${Math.round((task.progress || 0) * 100)}%` }} />
        </div>
      </div>

      {task.artifacts.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
          <span className="text-slate-400">
            {L("Tip: click a step to jump to its artifact", "提示：点击流程节点可跳到该步的产出物")}
          </span>
          <button onClick={() => scrollToEl("artifacts")} className="font-medium text-blue-600 hover:underline">
            {L(`↓ View artifacts (${task.artifacts.length})`, `↓ 查看产出物（${task.artifacts.length}）`)}
          </button>
        </div>
      )}

      <div className="card h-48 p-0">
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}
          nodesDraggable={false} nodesConnectable={false} zoomOnScroll={false} panOnDrag
          onNodeClick={onNodeClick}>
          <Background />
        </ReactFlow>
      </div>

      <div className="flex gap-2">
        {["FAILED", "SUSPENDED", "DONE"].includes(task.status) && (
          <button className="btn-primary"
            onClick={() => post(`/api/tasks/${id}/rerun`, {}).then(() => { toast(t("taskDetail.requeued"), "success"); load(); })}>
            {t("taskDetail.rerun")}
          </button>
        )}
        {["QUEUED", "SUSPENDED", "WAITING_APPROVAL"].includes(task.status) && (
          <button className="btn-ghost"
            onClick={() => post(`/api/tasks/${id}/cancel`, {}).then(() => { toast(t("taskDetail.cancelled"), "info"); load(); })}>
            {t("taskDetail.cancel")}
          </button>
        )}
      </div>

      {task.error && (
        <div className="card border-red-200 bg-red-50 text-sm text-red-700 whitespace-pre-wrap">
          {task.error}
        </div>
      )}

      <h2 id="artifacts" className="scroll-mt-4 text-lg font-semibold">
        {t("taskDetail.artifacts")}
        {task.artifacts.length > 0 ? ` · ${task.artifacts.length}` : ""}
      </h2>
      <div className="space-y-2">
        {task.artifacts.map((a: any, i: number) => (
          <details key={i} id={`artifact-${i}`} className="card scroll-mt-4" open={i === 0}>
            <summary className="cursor-pointer text-sm font-medium">
              {a.name} <span className="text-xs text-slate-400">· {a.step} · {fmtTime(a.ts)}</span>
            </summary>
            <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-700">
              {a.content}
            </pre>
          </details>
        ))}
        {task.artifacts.length === 0 && <p className="text-sm text-slate-400">{t("taskDetail.noArtifacts")}</p>}
      </div>
    </div>
  );
}
