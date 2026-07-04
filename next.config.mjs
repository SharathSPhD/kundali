/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // In local dev, forward engine calls to the FastAPI dev server.
    // In production on Vercel, vercel.json routes /api/py/* to the Python
    // function, so no rewrite is emitted here.
    if (process.env.NODE_ENV === "development") {
      const api = process.env.API_BASE_URL || "http://localhost:8000";
      return [
        { source: "/api/py/health", destination: `${api}/health` },
        { source: "/api/py/:path*", destination: `${api}/api/:path*` },
      ];
    }
    return [];
  },
};

export default nextConfig;
