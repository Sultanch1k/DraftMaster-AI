import createNextIntlPlugin from 'next-intl/plugin';

/** @type {import('next').NextConfig} */
const API_TARGET = process.env.API_PROXY_TARGET || 'http://127.0.0.1:12001';

const nextConfig = {
  reactStrictMode: true,
  // Standalone output produces a self-contained server bundle for the Docker
  // image; Vercel ignores it and builds normally.
  output: 'standalone',
  // When the dev server is reached through a tunnel or a different hostname,
  // Next blocks its HMR/dev resources by default. Origins are opt-in via env so
  // no hostname is baked into the repository.
  allowedDevOrigins: (process.env.DRAFTMASTER_DEV_ORIGINS ?? '').split(',').filter(Boolean),
  // Proxy the API through the Next server so the browser only ever talks to a
  // single origin (no CORS, no exposed backend port, works behind any tunnel).
  async rewrites() {
    return [{ source: '/api/:path*', destination: `${API_TARGET}/api/:path*` }];
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'cdn.cloudflare.steamstatic.com' },
      { protocol: 'https', hostname: 'cdn.steamstatic.com' },
    ],
  },
};

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

export default withNextIntl(nextConfig);
