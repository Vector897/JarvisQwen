"use client";

/** 共享的加载骨架与空状态组件，统一各页面的加载/空态观感。 */

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton h-16 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ icon = "📭", title, hint }: { icon?: string; title: string; hint?: string }) {
  return (
    <div className="card flex flex-col items-center gap-2 py-10 text-center">
      <div className="text-4xl">{icon}</div>
      <div className="font-medium text-slate-700">{title}</div>
      {hint && <div className="max-w-md text-sm text-slate-400">{hint}</div>}
    </div>
  );
}
