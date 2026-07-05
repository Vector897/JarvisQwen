"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

type Handler = (type: string, data: any) => void;
type Status = "connecting" | "online" | "offline";

const EVENT_TYPES = [
  "task_progress", "task_done", "task_failed", "task_suspended",
  "budget_alert", "briefing_ready", "approval_needed", "task_zombie_requeued",
];

const EventsCtx = createContext<{ status: Status; subscribe: (h: Handler) => () => void }>({
  status: "connecting",
  subscribe: () => () => {},
});
export const useEvents = () => useContext(EventsCtx);

/** 单一全局 SSE 连接，页面通过 subscribe 订阅，避免每页各开一条连接。 */
export function EventsProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("connecting");
  const handlers = useRef<Set<Handler>>(new Set());
  const pathname = usePathname();

  useEffect(() => {
    if (pathname === "/login" || pathname === "/home") return; // 未登录页不建连（避免 401 重连风暴）
    const es = new EventSource("/api/events");
    es.onopen = () => setStatus("online");
    es.onerror = () => setStatus("offline"); // 浏览器会自动重连
    for (const t of EVENT_TYPES) {
      es.addEventListener(t, (e) => {
        const data = JSON.parse((e as MessageEvent).data);
        handlers.current.forEach((h) => h(t, data));
      });
    }
    return () => es.close();
  }, [pathname]);

  const subscribe = (h: Handler) => {
    handlers.current.add(h);
    return () => {
      handlers.current.delete(h);
    };
  };

  return <EventsCtx.Provider value={{ status, subscribe }}>{children}</EventsCtx.Provider>;
}
