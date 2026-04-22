import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["mapbox-gl", "react-map-gl"],
  experimental: {
    // Static + server rendering
  },
  async rewrites() {
    // Proxy /api/* to the FastAPI backend during local dev
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
