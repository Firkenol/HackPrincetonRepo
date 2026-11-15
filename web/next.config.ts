import type { NextConfig } from "next";

// STATIC_EXPORT=1 builds the console as plain static files (web/out) for a static host
// such as GitHub Pages. BASE_PATH is the path it is served under, for example
// /offspec-demo. Without STATIC_EXPORT the build is the normal Next.js server build.
const staticExport = process.env.STATIC_EXPORT === "1";

const nextConfig: NextConfig = {
  ...(staticExport
    ? { output: "export" as const, basePath: process.env.BASE_PATH || undefined, trailingSlash: true, images: { unoptimized: true } }
    : // partial prerendering cannot be combined with a static export
      { cacheComponents: true, partialPrefetching: true }),
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
