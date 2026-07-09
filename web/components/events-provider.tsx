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

/** A single global SSE connection; pages subscribe via subscribe(), avoiding one connection per page. */
export function EventsProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("connecting");
  const handlers = useRef<Set<Handler>>(new Set());
  const pathname = usePathname();

  useEffect(() => {
    if (pathname === "/login" || pathname === "/home") return; // Don't connect on unauthenticated pages (avoids a 401 reconnect storm)
    const es = new EventSource("/api/events");
    es.onopen = () => setStatus("online");
    es.onerror = () => setStatus("offline"); // The browser reconnects automatically
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
