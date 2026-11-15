import { ImageResponse } from 'next/og';
import { loadOgFonts } from '@/lib/og-fonts';
import { buildPosterData, POSTER_FORMATS, type PosterFormat } from '@/lib/poster';
import { fromPanic } from '@/lib/winplan';
import { fetchPanicPlan } from '@/lib/plan-server';

export const runtime = 'nodejs';
export const contentType = 'image/png';

/**
 * Social poster for a fresh draft (the "I'm last pick" / share moment).
 *
 * The plan is recomputed server-side for the exact draft the user has on screen.
 * Hero artwork is embedded by the renderer, so the poster looks like a designed
 * card rather than a cropped screenshot.
 *
 * Query: `e` (enemy ids, comma-separated), `h` (optional hero id), `role`, `rk`
 * (rank tier), `locale`, `format` (story | square | portrait).
 */
function parseIntList(value: string | null): number[] {
  if (!value) return [];
  return value
    .split(',')
    .map((v) => Number(v.trim()))
    .filter((n) => Number.isInteger(n) && n > 0)
    .slice(0, 5);
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const enemies = parseIntList(url.searchParams.get('e'));
  const role = url.searchParams.get('role') || undefined;
  const rankTier = Number(url.searchParams.get('rk')) || undefined;
  const locale = url.searchParams.get('locale') === 'ru' ? 'ru' : 'en';
  const format = (url.searchParams.get('format') as PosterFormat) || 'story';

  if (enemies.length === 0 || !(format in POSTER_FORMATS)) {
    return new Response('Invalid poster request', { status: 400 });
  }

  const result = await fetchPanicPlan(enemies, role, rankTier, locale);
  if (!result) {
    return new Response('Plan unavailable', { status: 502 });
  }

  const data = buildPosterData(fromPanic(result), locale);
  const spec = POSTER_FORMATS[format];
  const fonts = await loadOgFonts();

  return new ImageResponse(spec.render(data), {
    width: spec.width,
    height: spec.height,
    fonts,
  });
}
