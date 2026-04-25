import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin Turbopack to this directory so it ignores stray lockfiles in parent dirs.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
