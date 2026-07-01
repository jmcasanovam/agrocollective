import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Genera server.js autocontenido para el Dockerfile multi-stage
  output: "standalone",
};

export default nextConfig;
