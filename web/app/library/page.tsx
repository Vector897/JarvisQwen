"use client";

import { useEffect, useState } from "react";
import { api, post } from "@/lib/api";
import { useToast } from "@/components/toast";
import { EmptyState, Skeleton } from "@/components/ui";

export default function Library() {
  const [papers, setPapers] = useState<any[] | null>(null);
  const [q, setQ] = useState("");
  const toast = useToast();

  const load = (query = "") =>
    api(`/api/library?q=${encodeURIComponent(query)}`).then(setPapers).catch(() => {});
  useEffect(() => { load(); }, []);

  async function syncZotero(id: string) {
    try {
      const r = await post(`/api/library/${id}/zotero-sync`, {});
      toast(r.message, "success");
    } catch (err: any) { toast(err.message, "error"); }
  }

  return (
    <div className="space-y-4">
      <QaBox />

      <form className="card flex gap-2" onSubmit={(e) => { e.preventDefault(); load(q); }}>
        <input className="input flex-1" value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="搜索已归档论文（标题/摘要）" />
        <button className="btn-primary">搜索</button>
        <a className="btn-ghost" href="/api/library/export?fmt=bibtex" download>
          导出 BibTeX
        </a>
      </form>

      {papers === null ? (
        <Skeleton rows={3} />
      ) : papers.length === 0 ? (
        <EmptyState icon="📚" title="知识库为空" hint="创建文献跟踪任务或添加订阅后会自动填充。" />
      ) : (
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
                <div className="flex flex-wrap items-center gap-3 pt-1">
                  <a href={p.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                    查看原文 →
                  </a>
                  <button className="btn-ghost text-xs" onClick={() => syncZotero(p.id)}>
                    同步到 Zotero
                  </button>
                </div>
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}

function QaBox() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{ answer: string; cited: any[]; escalated: boolean } | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setAnswer(null);
    try {
      const r = await post("/api/library/qa", { question });
      setAnswer(r);
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card space-y-2">
      <div className="font-medium">🔎 问知识库</div>
      <p className="text-xs text-slate-500">对已归档的全部论文提问，系统会检索相关证据并标注引用来源。</p>
      <form onSubmit={ask} className="flex gap-2">
        <input className="input flex-1" value={question} onChange={(e) => setQuestion(e.target.value)}
          placeholder="如：我库里关于灾难性遗忘的论文都提出了什么解决方案？" />
        <button className="btn-primary" disabled={busy}>{busy ? "检索中…" : "提问"}</button>
      </form>
      {answer && (
        <div className="rounded-lg bg-slate-50 p-3 text-sm">
          <div className="whitespace-pre-wrap">{answer.answer}</div>
          {answer.escalated && (
            <div className="mt-1 text-xs text-amber-600">（轻量层置信度不足，已自动升级到前沿模型重答）</div>
          )}
          {answer.cited.length > 0 && (
            <div className="mt-2 space-y-1 border-t border-slate-200 pt-2 text-xs">
              {answer.cited.map((c, i) => (
                <div key={c.id}>
                  [{i + 1}] <a href={c.url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">{c.title}</a>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
