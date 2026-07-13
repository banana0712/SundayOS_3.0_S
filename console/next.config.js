/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  // API routes are not included in static export — the browser calls
  // the backend directly with X-API-Key header (see lib/api-key.ts).
};

module.exports = nextConfig;