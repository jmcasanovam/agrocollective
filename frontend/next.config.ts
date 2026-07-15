import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera server.js autocontenido para el Dockerfile multi-stage
  output: "standalone",
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
      };
    }
    return config;
  },
};

export default nextConfig;
