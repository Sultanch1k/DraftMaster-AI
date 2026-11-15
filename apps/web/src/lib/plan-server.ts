import type { PanicResult } from './types';

/**
 * Server-side strategy fetcher for the social poster.
 *
 * The poster is rendered as an image on the server (Next `next/og`), so it must
 * fetch the plan itself rather than receive it from the browser.
 *
 * It renders *only* through a signed share token (`GET /api/share/{token}`),
 * which is quota-free by design: the token could only be minted by an
 * authenticated, quota-paying request, so rendering it again costs nothing. The
 * server must never call `/api/panic` directly — that endpoint charges quota and
 * every server-side render would share one anonymous bucket (the renderer's IP),
 * starving every user's poster after three drafts a day.
 */
function origin(): string {
  return (
    process.env.API_PROXY_TARGET ||
    process.env.DRAFTMASTER_API_ORIGIN ||
    'http://127.0.0.1:12001'
  );
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
