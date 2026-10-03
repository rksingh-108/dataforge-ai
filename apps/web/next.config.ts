import type { NextConfig } from "next";

/**
 * The web app talks to the API only from the server (BFF): browsers hit
 * same-origin `/api/*` route handlers, which proxy to Django with the access
 * token held in an httpOnly cookie. This means no CORS handling in the browser
 * and no token ever exposed to JavaScript.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Emit a self-contained server bundle so the Docker image does not need the
  // full node_modules tree at runtime.
  output: "standalone",
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
