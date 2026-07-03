"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, Skeleton } from "@/components/ui";
import { useLang } from "@/lib/i18n";

export default function Briefings() {
  const [items, setItems] = useState<any[] | null>(null);
  const { t } = useLang();
  useEffect(() => { api("/api/briefings").then(setItems).catch(() => {}); }, []);

  if (items === null) return <Skeleton rows={3} />;
  if (items.length === 0) {
    return <EmptyState icon="📰" title={t("briefings.empty")} hint={t("briefings.emptyHint")} />;
  }

  return (
    <div className="space-y-4">
      {items.map((b) => (
        <details key={b.id} className="card" open={items[0]?.id === b.id}>
          <summary className="flex flex-wrap items-center gap-2">
            <span className="cursor-pointer font-medium">📰 {b.date}</span>
            <span className="ml-auto flex gap-2 text-xs">
              <a className="btn-ghost px-2 py-1" href={`/api/briefings/${b.id}/export?fmt=md`} download
                onClick={(e) => e.stopPropagation()}>{t("briefings.exportMd")}</a>
              <a className="btn-ghost px-2 py-1" href={`/api/briefings/${b.id}/export?fmt=pdf`} download
                onClick={(e) => e.stopPropagation()}>{t("briefings.exportPdf")}</a>
            </span>
          </summary>
          <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{b.content_md}</div>
        </details>
      ))}
    </div>
  );
}
