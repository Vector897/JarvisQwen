"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function Briefings() {
  const [items, setItems] = useState<any[]>([]);
  useEffect(() => { api("/api/briefings").then(setItems).catch(() => {}); }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">简报</h1>
      {items.map((b) => (
        <details key={b.id} className="card" open={items[0]?.id === b.id}>
          <summary className="cursor-pointer font-medium">📰 {b.date} 简报</summary>
          <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed">{b.content_md}</div>
        </details>
      ))}
      {items.length === 0 && (
        <p className="text-sm text-slate-400">
          暂无简报。系统每天早晨自动生成；也可以在任务页输入"生成简报"立即触发。
        </p>
      )}
    </div>
  );
}
