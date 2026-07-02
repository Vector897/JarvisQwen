"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Library() {
  const [papers, setPapers] = useState<any[]>([]);
  const [q, setQ] = useState("");

  const load = (query = "") =>
    api(`/api/library?q=${encodeURIComponent(query)}`).then(setPapers).catch(() => {});
  useEffect(() => { load(); }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">知识库</h1>
      <form className="card flex gap-2" onSubmit={(e) => { e.preventDefault(); load(q); }}>
        <input className="input flex-1" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="搜索已归档论文（标题/摘要）" />
        <button className="btn-primary">搜索</button>
      </form>
      <div className="space-y-2">
        {papers.map((p) => (
          <details key={p.id} className="card">
            <summary className="cursor-pointer">
              <span className="font-medium">{p.title}</span>
              <span className="ml-2 text-xs text-slate-400">
                {p.published_at}{p.has_pdf ? " · PDF已归档" : ""}
              </span>
            </summary>
            <div className="mt-2 space-y-2 text-sm">
              <p className="text-xs text-slate-500">{p.authors}</p>
              {p.summary_md ? (
                <div className="whitespace-pre-wrap rounded-lg bg-slate-50 p-3">{p.summary_md}</div>
              ) : (
                <p className="text-slate-500">{p.abstract}</p>
              )}
              <a href={p.url} target="_blank" rel="noreferrer"
                className="text-blue-600 hover:underline">查看原文 →</a>
            </div>
          </details>
        ))}
        {papers.length === 0 && <p className="text-sm text-slate-400">知识库为空。创建文献跟踪任务或订阅后会自动填充。</p>}
      </div>
    </div>
  );
}
