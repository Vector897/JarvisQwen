"use client";

import { useEffect, useState } from "react";
import { api, fmtTime } from "@/lib/api";

export default function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  useEffect(() => { api("/api/audit").then(setRows).catch(() => {}); }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">审计流水</h1>
      <p className="text-sm text-slate-500">每一次 LLM 出境调用的模型、token、费用与输入输出摘要（append-only）。</p>
      <div className="space-y-2">
        {rows.map((r) => (
          <details key={r.id} className="card text-sm">
            <summary className="flex cursor-pointer flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{fmtTime(r.ts)}</span>
              <span className="badge bg-slate-100">{r.model}</span>
              {r.step && <span className="text-xs text-slate-400">{r.step}</span>}
              <span className="ml-auto font-mono text-xs">
                {r.cached ? "缓存命中 · $0" : r.simulated ? "dry-run · $0" :
                  `${r.tokens_in}→${r.tokens_out} tok · $${r.cost_usd}`}
              </span>
            </summary>
            <div className="mt-2 space-y-1 text-xs text-slate-600">
              <p><b>输入：</b>{r.input_digest}</p>
              <p><b>输出：</b>{r.output_digest}</p>
            </div>
          </details>
        ))}
        {rows.length === 0 && <p className="text-sm text-slate-400">暂无调用记录。</p>}
      </div>
    </div>
  );
}
