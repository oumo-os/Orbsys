import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Docker standalone image
  output: "standalone",

  async rewrites() {
    // NEXT_PUBLIC_API_URL is baked at build time for the client.
    // For server-side rewrites inside Docker, use the service name.
    const apiUrl = process.env.API_REWRITE_URL
      || process.env.NEXT_PUBLIC_API_URL
      || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
