import type { Metadata, Viewport } from "next";
import "./globals.css";
import Nav from "@/components/nav";
import { Topbar } from "@/components/topbar";
import { ToastProvider } from "@/components/toast";
import { EventsProvider } from "@/components/events-provider";
import { ThemeProvider, THEME_INIT_SCRIPT } from "@/components/theme-provider";
import { LangProvider } from "@/lib/i18n";

export const metadata: Metadata = {
  title: "AAOS 控制台",
  description: "AI Agent Operating System — 云边协同的 Agent 控制平面",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0f172a",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        {/* 防止深色模式在水合前闪一下浅色 */}
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body>
        <ThemeProvider>
          <LangProvider>
            <ToastProvider>
              <EventsProvider>
                <div className="flex min-h-screen flex-col md:flex-row">
                  <Nav />
                  <div className="flex min-w-0 flex-1 flex-col">
                    <Topbar />
                    <main className="mx-auto w-full max-w-6xl flex-1 p-4 pb-24 md:p-8 md:pb-8">
                      {children}
                    </main>
                  </div>
                </div>
              </EventsProvider>
            </ToastProvider>
          </LangProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
