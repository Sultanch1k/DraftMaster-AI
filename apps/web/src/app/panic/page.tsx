import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { SeoHeader } from '@/components/SeoHeader';
import { PanicLanding } from '@/components/PanicLanding';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('panicLanding');
  const title = t('title');
  const description = t('description');
  return {
    title,
    description,
    alternates: { canonical: '/panic' },
    openGraph: { title, description, url: `${BASE}/panic`, type: 'website' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

/**
 * Public landing page for the flagship "I'M LAST PICK" flow.
 *
 * This is the highest-intent acquisition page: someone searching "last pick
 * dota" is mid-draft and needs an answer now. It runs the real tool rather than
 * describing it, because the product demo *is* the pitch.
 */
export default async function PanicPage() {
  const t = await getTranslations('panicLanding');
  return (
    <div className="min-h-dvh">
      <SeoHeader />
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6">
        <section className="max-w-3xl">
          <span className="chip border-dire/50 text-dire">🚨 {t('badge')}</span>
          <h1 className="mt-3 text-3xl font-black leading-tight text-white sm:text-4xl">{t('title')}</h1>
          <p className="mt-2 text-sm text-slate-400 sm:text-base">{t('description')}</p>
        </section>
        <PanicLanding />
      </main>
    </div>
  );
}
