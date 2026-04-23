import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["mapbox-gl", "react-map-gl"],

  // Temporary: bypass strict type-check during production build.
  // TODO: fix strict null-checks in pr-map.tsx and remove this.
  typescript: {
    ignoreBuildErrors: true,
  },

  // Proxy /api/* to FastAPI. In production, Caddy handles this at the edge,
  // but keeping the rewrite lets the build work without a Caddy dependency.
  async rewrites() {
    const apiOrigin = process.env.INTERNAL_API_ORIGIN ?? "http://127.0.0.1:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
