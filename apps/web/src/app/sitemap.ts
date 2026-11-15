import type { MetadataRoute } from 'next';
import { allSeoHeroes } from '@/lib/seo';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  // The programmatic counter and guide pages are the main organic acquisition
  // surface, so they all belong in the sitemap with a stable priority.
  const counterPages = allSeoHeroes.map((h) => ({
    url: `${BASE}/counter/${h.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.7,
  }));
  const guidePages = allSeoHeroes.map((h) => ({
    url: `${BASE}/hero/${h.slug}`,
    lastModified: now,
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }));
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${BASE}/panic`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${BASE}/meta`, lastModified: now, changeFrequency: 'daily', priority: 0.8 },
    { url: `${BASE}/privacy`, lastModified: now, changeFrequency: 'yearly', priority: 0.2 },
    { url: `${BASE}/terms`, lastModified: now, changeFrequency: 'yearly', priority: 0.2 },
    { url: `${BASE}/refund`, lastModified: now, changeFrequency: 'yearly', priority: 0.2 },
  ];
  return [
    {
      url: BASE,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 1,
    },
    ...staticPages,
    ...counterPages,
    ...guidePages,
  ];
}
