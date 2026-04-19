import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Backend API is on a separate origin in production.
  // In dev, NEXT_PUBLIC_API_URL=http://localhost:8000
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
    return [
      {
        // Proxy /api/* to the FastAPI backend so the browser never needs CORS
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

export default nextConfig
