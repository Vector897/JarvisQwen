import type { NextConfig } from "next";

// Mode A (co-located VM deployment): BACKEND_URL=http://server:8000 (docker internal network)
// Mode B (Vercel frontend): set BACKEND_URL=https://your-VM-domain in the Vercel environment variables
const backend = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone", // For Docker deployment; automatically ignored on Vercel
  async rewrites() {
    // Key design: reverse-proxy /api/* to the backend → same-origin from the browser's view, no cross-origin issues for cookies/SSE
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
