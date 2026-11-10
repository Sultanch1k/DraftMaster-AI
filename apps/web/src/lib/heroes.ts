import raw from '@/data/hero-counters.json';

/**
 * Hero id -> display name / slug, for rendering share links server-side.
 *
 * Shares encode only ids (short, stable URLs). This maps them back to names
 * for the OG image and page copy without an API round trip, using the same
 * committed dataset the SEO pages already rely on.
 */
type HeroEntry = { id: number; name: string; slug: string; icon: string | null };

const BY_ID = new Map<number, HeroEntry>();
for (const hero of Object.values((raw as { heroes: Record<string, HeroEntry> }).heroes)) {
  BY_ID.set(hero.id, hero);
}

export function heroName(id: number): string | null {
  return BY_ID.get(id)?.name ?? null;
}

export function heroSlug(id: number): string | null {
  return BY_ID.get(id)?.slug ?? null;
}

export function heroIcon(id: number): string | null {
  return BY_ID.get(id)?.icon ?? null;
}

const SLUG_BY_NAME = new Map<string, string>();
for (const hero of Object.values((raw as { heroes: Record<string, HeroEntry> }).heroes)) {
  SLUG_BY_NAME.set(hero.name.toLowerCase(), hero.slug);
}

/** Resolve a display name ("Anti-Mage") to its SEO slug ("anti-mage"). */
export function slugForName(name: string): string | null {
  return SLUG_BY_NAME.get(name.trim().toLowerCase()) ?? null;
}
