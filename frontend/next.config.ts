import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",   // Docker: a self-contained server (Vercel ignores this)
  poweredByHeader: false,
};

export default nextConfig;
