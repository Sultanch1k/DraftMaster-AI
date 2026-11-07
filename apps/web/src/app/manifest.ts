import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'DraftMaster AI',
    short_name: 'DraftMaster',
    description: 'The Dota 2 AI coach that tells you how to win the game — not just which hero to pick.',
    start_url: '/',
    display: 'standalone',
    background_color: '#07090d',
    theme_color: '#07090d',
    icons: [{ src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }],
  };
}
