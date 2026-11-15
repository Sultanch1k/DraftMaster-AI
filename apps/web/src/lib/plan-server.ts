import type { PanicResult } from './types';

/**
 * Server-side strategy fetchers for the social poster.
 *
 * The poster is rendered as an image on the server (Next `next/og`), so it must
 * fetch the plan itself rather than receive it from the browser. It calls the
 * same FastAPI endpoints the app proxies to, with the internal origin.
 *
 * Only *ephemeral rendering* happens here — no entitlement is minted and no
 * quota is charged (the caller already paid for the plan it is rendering).
 */
function origin(): string {
  return (
    process.env.API_PROXY_TARGET ||
    process.env.DRAFTMASTER_API_ORIGIN ||
    'http://127.0.0.1:12001'
  );
}

async function postJson<T>(path: string, body: unknown, locale: string): Promise<T | null> {
  try {
    const res = await fetch(`${origin()}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-locale': locale === 'ru' ? 'ru' : 'en' },
      body: JSON.stringify(body),
      // Posters are regenerated on demand; do not cache a stale plan.
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export function fetchPanicPlan(
  enemyIds: number[],
  role: string | undefined,
  rank: number | undefined,
  locale: string,
): Promise<PanicResult | null> {
  return postJson<PanicResult>('/api/panic', { enemy_hero_ids: enemyIds, role, rank_tier: rank }, locale);
}

/** Render the plan behind a signed share token (no quota charged by the API). */
export async function fetchSharedPlan(token: string, locale: string): Promise<PanicResult | null> {
  try {
    const res = await fetch(`${origin()}/api/share/${encodeURIComponent(token)}`, {
      headers: { 'x-locale': locale === 'ru' ? 'ru' : 'en' },
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return (await res.json()) as PanicResult;
  } catch {
    return null;
  }
}
