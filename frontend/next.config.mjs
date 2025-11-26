/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: 'standalone',
  
  // Environment variables are automatically available via NEXT_PUBLIC_ prefix
  // No additional configuration needed for NEXT_PUBLIC_API_URL and NEXT_PUBLIC_WS_URL
  
  // Optional: API proxy configuration (uncomment if needed to avoid CORS in development)
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`,
  //     },
  //   ];
  // },
};

export default nextConfig;
