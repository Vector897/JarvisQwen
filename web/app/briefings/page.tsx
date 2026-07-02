"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState, Skeleton } from "@/components/ui";

export default function Briefings() {
  const [items, setItems] = useState<any[] | null>(null);
  useEffect(() => { api("/api/briefings").then(setItems).catch(() => {}); }, []);

  if (items === null) return <Skeleton rows={3} />;
  if (items.length === 0) {
    return <EmptyState icon="📰" title="暂无简报"
      hint='系统每天早晨自动生成；也可以在任务页输入"生成简报"立即触发。' />;
  }

  return (
    <div className="space-y-4">
      {items.map((b) => (
        <details key={b.id} className="card" open={items[0]?.id === b.id}>
          <summary className="flex flex-wrap items-center gap-2">
            <span className="cursor-pointer font-medium">📰 {b.date} 简报</span>
            <span className="ml-auto flex gap-2 text-xs">
              <a className="btn-ghost px-2 py-1" href={`/api/briefings/${b.id}/export?fmt=md`} download
                onClick={(e) => e.stopPropagation()}>导出 MD</a>
              <a className="btn-ghost px-2 py-1" href={`/api/briefings/${b.id}/export?fmt=pdf`} download
                onClick={(e) => e.stopPropagation()}>导出 PDF</a>
            </span>
          </summary>
          <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{b.content_md}</div>
        </details>
      ))}
    </div>
  );
}
