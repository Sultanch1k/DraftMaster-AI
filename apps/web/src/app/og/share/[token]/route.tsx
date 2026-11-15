import { ImageResponse } from 'next/og';
import { loadOgFonts } from '@/lib/og-fonts';
import { buildPosterData, POSTER_FORMATS, type PosterFormat } from '@/lib/poster';
import { fetchSharedPlan } from '@/lib/plan-server';

export const runtime = 'nodejs';
export const contentType = 'image/png';

/**
 * Social poster for a *shared* plan, keyed by the signed share token.
 *
 * This is the image a shared link advertises: it renders the same plan the link
 * opens, so a poster and its landing page can never disagree. Because the token
 * is signed, no quota is charged here.
 */
export async function GET(request: Request, { params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const url = new URL(request.url);
  const locale = url.searchParams.get('locale') === 'ru' ? 'ru' : 'en';
  const format = (url.searchParams.get('format') as PosterFormat) || 'portrait';

  if (!(format in POSTER_FORMATS)) {
    return new Response('Invalid format', { status: 400 });
  }

  const plan = await fetchSharedPlan(token, locale);
  if (!plan) {
    return new Response('Plan unavailable', { status: 404 });
  }

  const data = buildPosterData(plan, locale);
  const spec = POSTER_FORMATS[format];
  const fonts = await loadOgFonts();

  return new ImageResponse(spec.render(data), {
    width: spec.width,
    height: spec.height,
    fonts,
  });
}
