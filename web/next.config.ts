import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  // Keep Next from walking up to a lockfile outside web/.
  turbopack: { root: import.meta.dirname },
};

export default config;
