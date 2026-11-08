import { NextResponse } from 'next/server';
import { isLocale, LOCALE_COOKIE } from '@/i18n/config';

/**
 * Persist the user's language choice.
 *
 * Written as a route handler (rather than a server action) so the switcher can
 * be a plain fetch + router.refresh(), which keeps the client component free of
 * server-action plumbing.
 */
export async function POST(request: Request) {
  const body = (await request.json().catch(() => ({}))) as { locale?: string };
  const locale = isLocale(body.locale) ? body.locale : null;
  if (!locale) {
    return NextResponse.json({ ok: false, error: 'unsupported locale' }, { status: 400 });
  }

  const response = NextResponse.json({ ok: true, locale });
  response.cookies.set({
    name: LOCALE_COOKIE,
    value: locale,
    path: '/',
    maxAge: 60 * 60 * 24 * 365,
    sameSite: 'lax',
  });
  return response;
}
