import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  poweredByHeader: false,
  // unpdf loads `unpdf/pdfjs` dynamically; bundling it breaks in API routes.
  serverExternalPackages: ["unpdf"],
};

export default nextConfig;
