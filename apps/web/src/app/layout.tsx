import type { Metadata, Viewport } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages, getTranslations } from 'next-intl/server';
import './globals.css';

// The locale lives in a cookie rather than the URL, so every page renders per
// request. This keeps a single route tree (no /[locale] segment) and makes the
// language switch instant.
export const dynamic = 'force-dynamic';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('meta');
  return {
    title: t('title'),
    description: t('description'),
    applicationName: 'DraftMaster AI',
    openGraph: {
      title: 'DraftMaster AI',
      description: t('description'),
      type: 'website',
    },
  };
}

export const viewport: Viewport = {
  themeColor: '#07090d',
  width: 'device-width',
  initialScale: 1,
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [locale, messages] = await Promise.all([getLocale(), getMessages()]);
  return (
    <html lang={locale} className="dark">
      <body className="min-h-dvh font-sans antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
