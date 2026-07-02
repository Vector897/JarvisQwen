"use client";

import { createContext, useCallback, useContext, useState } from "react";

type Kind = "info" | "success" | "error";
type Toast = { id: number; msg: string; kind: Kind };

const ToastCtx = createContext<(msg: string, kind?: Kind) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

const STYLE: Record<Kind, string> = {
  info: "bg-slate-800 text-white",
  success: "bg-emerald-600 text-white",
  error: "bg-red-600 text-white",
};
const ICON: Record<Kind, string> = { info: "ℹ️", success: "✓", error: "✕" };

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const push = useCallback((msg: string, kind: Kind = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, msg, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div className="fixed bottom-20 right-4 z-[100] flex flex-col gap-2 md:bottom-4">
        {toasts.map((t) => (
          <div key={t.id}
            className={`animate-toast flex max-w-xs items-start gap-2 rounded-lg px-4 py-2.5 text-sm shadow-lg ${STYLE[t.kind]}`}>
            <span>{ICON[t.kind]}</span>
            <span className="whitespace-pre-wrap break-words">{t.msg}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
