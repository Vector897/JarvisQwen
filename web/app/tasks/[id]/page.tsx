"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ReactFlow, Background, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { api, post, subscribeEvents, fmtEta, fmtTime, STATUS_LABEL } from "@/lib/api";

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

  const load = useCallback(() => api(`/api/tasks/${id}`).then(setTask).catch(() => {}), [id]);

  useEffect(() => {
    load();
    const off = subscribeEvents((type, ev) => {
      if (ev.task_id !== id) return;
      if (ev.sub_progress) setSub(ev.sub_progress);
      load();
    });
    return off;
  }, [id, load]);

  if (!task) return <p className="text-slate-400">加载中…</p>;
  const [label, cls] = STATUS_LABEL[task.status] || [task.status, "bg-slate-100"];

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
          <span>总进度 {Math.round((task.progress || 0) * 100)}%{sub ? ` · ${sub}` : ""}</span>
          <span className="text-slate-500">
            {task.status === "RUNNING" && task.eta_ts ? fmtEta(task.eta_ts) : ""}
            {task.status === "DONE" ? `完成于 ${fmtTime(task.finished_at)}` : ""}
          </span>
        </div>
        <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div className="h-full bg-blue-500 transition-all"
            style={{ width: `${Math.round((task.progress || 0) * 100)}%` }} />
        </div>
      </div>

      <div className="card h-48 p-0">
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}
          nodesDraggable={false} nodesConnectable={false} zoomOnScroll={false} panOnDrag>
          <Background />
        </ReactFlow>
      </div>

      <div className="flex gap-2">
        {["FAILED", "SUSPENDED", "DONE"].includes(task.status) && (
          <button className="btn-primary" onClick={() => post(`/api/tasks/${id}/rerun`, {}).then(load)}>
            从检查点重跑
          </button>
        )}
        {["QUEUED", "SUSPENDED", "WAITING_APPROVAL"].includes(task.status) && (
          <button className="btn-ghost" onClick={() => post(`/api/tasks/${id}/cancel`, {}).then(load)}>
            取消任务
          </button>
        )}
      </div>

      {task.error && (
        <div className="card border-red-200 bg-red-50 text-sm text-red-700 whitespace-pre-wrap">
          {task.error}
        </div>
      )}

      <h2 className="text-lg font-semibold">产出物（Artifacts）</h2>
      <div className="space-y-2">
        {task.artifacts.map((a: any, i: number) => (
          <details key={i} className="card">
            <summary className="cursor-pointer text-sm font-medium">
              {a.name} <span className="text-xs text-slate-400">· {a.step} · {fmtTime(a.ts)}</span>
            </summary>
            <pre className="mt-2 max-h-80 overflow-auto whitespace-pre-wrap text-xs text-slate-700">
              {a.content}
            </pre>
          </details>
        ))}
        {task.artifacts.length === 0 && <p className="text-sm text-slate-400">暂无产出物。</p>}
      </div>
    </div>
  );
}
