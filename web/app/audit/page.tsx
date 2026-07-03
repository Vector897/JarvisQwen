"use client";

import { useEffect, useState } from "react";
import { api, fmtTime } from "@/lib/api";
import { useLang } from "@/lib/i18n";

export default function Audit() {
  const [rows, setRows] = useState<any[]>([]);
  const { t } = useLang();
  useEffect(() => { api("/api/audit").then(setRows).catch(() => {}); }, []);

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">{t("audit.hint")}</p>
      <div className="space-y-2">
        {rows.map((r) => (
          <details key={r.id} className="card text-sm">
            <summary className="flex cursor-pointer flex-wrap items-center gap-2">
              <span className="font-mono text-xs">{fmtTime(r.ts)}</span>
              <span className="badge bg-slate-100">{r.model}</span>
              {r.step && <span className="text-xs text-slate-400">{r.step}</span>}
              <span className="ml-auto font-mono text-xs">
                {r.cached ? `${t("audit.cacheHit")} · $0` : r.simulated ? `${t("audit.dryRun")} · $0` :
                  `${r.tokens_in}→${r.tokens_out} tok · $${r.cost_usd}`}
              </span>
            </summary>
            <div className="mt-2 space-y-1 text-xs text-slate-600">
              <p><b>{t("audit.input")}</b>{r.input_digest}</p>
              <p><b>{t("audit.output")}</b>{r.output_digest}</p>
            </div>
          </details>
        ))}
        {rows.length === 0 && <p className="text-sm text-slate-400">{t("audit.empty")}</p>}
      </div>
    </div>
  );
}
