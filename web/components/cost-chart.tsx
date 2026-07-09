"use client";

/** Lightweight hand-drawn SVG column/bar charts, with no extra charting-library dependency. */

export function BarChart({ data, height = 140 }: { data: { date: string; cost_usd: number }[]; height?: number }) {
  const max = Math.max(...data.map((d) => d.cost_usd), 0.001);
  const barWidth = 100 / data.length;
  return (
    <div>
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className="w-full" style={{ height }}>
        {data.map((d, i) => {
          const h = (d.cost_usd / max) * (height - 20);
          return (
            <g key={i}>
              <rect x={i * barWidth + barWidth * 0.15} y={height - 20 - h}
                width={barWidth * 0.7} height={h} rx={1}
                className="fill-blue-500 dark:fill-blue-400" />
            </g>
          );
        })}
      </svg>
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        {data.filter((_, i) => i % Math.ceil(data.length / 6 || 1) === 0).map((d) => (
          <span key={d.date}>{d.date}</span>
        ))}
      </div>
    </div>
  );
}

const PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#64748b"];

export function ModelBreakdown({ data }: { data: { model: string; cost_usd: number }[] }) {
  const total = data.reduce((s, d) => s + d.cost_usd, 0) || 1;
  return (
    <div className="space-y-1.5">
      {data.map((d, i) => {
        const pct = (d.cost_usd / total) * 100;
        return (
          <div key={d.model} className="flex items-center gap-2 text-xs">
            <span className="w-28 shrink-0 truncate font-mono">{d.model}</span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div className="h-full rounded-full" style={{ width: `${pct}%`, background: PALETTE[i % PALETTE.length] }} />
            </div>
            <span className="w-16 shrink-0 text-right font-mono">${d.cost_usd.toFixed(3)}</span>
          </div>
        );
      })}
      {data.length === 0 && <p className="text-xs text-slate-400">暂无调用记录</p>}
    </div>
  );
}
