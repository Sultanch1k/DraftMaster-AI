export const locales = ['en', 'ru'] as const;
export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = 'en';

export const LOCALE_COOKIE = 'draftmaster_locale';

/** Short labels for the header switcher. */
export const LOCALE_LABELS: Record<Locale, string> = {
  en: 'EN',
  ru: 'RU',
};

export function isLocale(value: string | undefined | null): value is Locale {
  return !!value && (locales as readonly string[]).includes(value);
}

/** Map a browser language tag ('ru-RU') to a supported locale. */
export function fromAcceptLanguage(header: string | null | undefined): Locale {
  if (!header) return defaultLocale;
  for (const part of header.split(',')) {
    const tag = part.split(';')[0].trim().toLowerCase().replace('_', '-');
    const base = tag.split('-')[0];
    if (isLocale(base)) return base;
  }
  return defaultLocale;
}
