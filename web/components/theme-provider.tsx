"use client";

import { createContext, useContext, useEffect, useState } from "react";

type Theme = "light" | "dark";
const ThemeCtx = createContext<{ theme: Theme; toggle: () => void }>({
  theme: "light",
  toggle: () => {},
});
export const useTheme = () => useContext(ThemeCtx);

/** 防闪烁：在首次渲染前同步读取 localStorage 并打上 class，放在 <head> 里内联执行。 */
export const THEME_INIT_SCRIPT = `
try {
  var t = localStorage.getItem('aaos-theme') ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  if (t === 'dark') document.documentElement.classList.add('dark');
} catch (e) {}
`;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const saved = (localStorage.getItem("aaos-theme") as Theme | null);
    if (saved) setTheme(saved);
    else if (document.documentElement.classList.contains("dark")) setTheme("dark");
  }, []);

  function toggle() {
    const next = theme === "light" ? "dark" : "light";
    setTheme(next);
    localStorage.setItem("aaos-theme", next);
    document.documentElement.classList.toggle("dark", next === "dark");
  }

  return <ThemeCtx.Provider value={{ theme, toggle }}>{children}</ThemeCtx.Provider>;
}
