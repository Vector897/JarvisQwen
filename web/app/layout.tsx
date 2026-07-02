import type { Metadata, Viewport } from "next";
import "./globals.css";
import Nav from "@/components/nav";

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
    <html lang="zh-CN">
      <body>
        <div className="flex min-h-screen flex-col md:flex-row">
          <Nav />
          <main className="flex-1 p-4 md:p-8 pb-20 md:pb-8 max-w-6xl w-full mx-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
