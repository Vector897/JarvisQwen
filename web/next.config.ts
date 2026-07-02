import type { NextConfig } from "next";

// 模式 A（同 VM 部署）：BACKEND_URL=http://server:8000（docker 内网）
// 模式 B（Vercel 前端）：在 Vercel 环境变量里设 BACKEND_URL=https://你的VM域名
const backend = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone", // Docker 部署用；Vercel 部署时自动忽略
  async rewrites() {
    // 关键设计：/api/* 反代到后端 → 浏览器视角同源，cookie/SSE 无跨域问题
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
