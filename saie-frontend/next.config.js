/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "saie-media.s3.eu-north-1.amazonaws.com",
      },
      {
        protocol: "https",
        hostname: "api.saie-clips.com",
      },
    ],
  },
};

module.exports = nextConfig;
