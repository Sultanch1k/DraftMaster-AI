import type { MetadataRoute } from 'next';
import { allSeoHeroes } from '@/lib/seo';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  // The programmatic counter pages are the main organic acquisition surface,
  // so they all belong in the sitemap with a stable priority.
  const counterPages = allSeoHeroes.map((h) => ({
    url: `${BASE}/counter/${h.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));
  return [
    {
      url: BASE,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1,
    },
    ...counterPages,
  ];
}
