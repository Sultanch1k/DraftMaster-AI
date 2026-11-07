import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';
import { defaultLocale, fromAcceptLanguage, isLocale, LOCALE_COOKIE } from './config';

/**
 * Resolve the request locale on the server.
 *
 * Preference order: the persisted cookie (the user's explicit choice), then the
 * browser's Accept-Language header, then English. The locale is never part of
 * the URL, so every page stays on a single route and links never break.
 */
export default getRequestConfig(async () => {
  const [cookieStore, headerStore] = await Promise.all([cookies(), headers()]);
  const cookieLocale = cookieStore.get(LOCALE_COOKIE)?.value;
  const locale = isLocale(cookieLocale)
    ? cookieLocale
    : fromAcceptLanguage(headerStore.get('accept-language')) || defaultLocale;

  return {
    locale,
    messages: (await import(`./messages/${locale}.json`)).default,
  };
});
