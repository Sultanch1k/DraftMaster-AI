import type { Metadata, Viewport } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages, getTranslations } from 'next-intl/server';
import './globals.css';

// The locale lives in a cookie rather than the URL, so the app shell renders
// per request and the language switch is instant. Individual routes can opt
// into static rendering (the /counter pages do) for crawlers and speed.

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('meta');
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';
  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: t('title'),
      template: '%s · DraftMaster AI',
    },
    description: t('description'),
    applicationName: 'DraftMaster AI',
    keywords: [
      'Dota 2',
      'draft',
      'counter pick',
      'Dota 2 coach',
      'item build',
      'win probability',
      'last pick',
      'Dota 2 AI',
    ],
    alternates: { canonical: '/' },
    openGraph: {
      title: 'DraftMaster AI',
      description: t('description'),
      type: 'website',
      siteName: 'DraftMaster AI',
      url: siteUrl,
    },
    twitter: {
      card: 'summary_large_image',
      title: 'DraftMaster AI',
      description: t('description'),
    },
    robots: { index: true, follow: true },
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
