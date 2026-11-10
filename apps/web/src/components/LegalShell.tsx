import Link from 'next/link';
import { getTranslations } from 'next-intl/server';

export const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL || 'support@draftmaster.wiki';
export const EFFECTIVE_DATE = '2026-11-07';

/**
 * Shared chrome for the legal pages. A payment provider will not approve a
 * store without reachable policies, and buyers trust a site that has them.
 */
export async function LegalShell({ title, children }: { title: string; children: React.ReactNode }) {
  const t = await getTranslations('legal');
  return (
    <div className="min-h-dvh">
      <header className="border-b border-base-800">
        <div className="mx-auto flex w-full max-w-3xl items-center justify-between px-4 py-4">
          <Link href="/" className="text-sm font-black tracking-tight text-white">
            DRAFT<span className="text-radiant">MASTER</span>
          </Link>
          <Link href="/" className="btn-ghost text-xs">
            {t('back')}
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl px-4 py-8">
        <h1 className="text-2xl font-black text-white sm:text-3xl">{title}</h1>
        <p className="mt-1 text-xs text-slate-500">{t('effective', { date: EFFECTIVE_DATE })}</p>
        <div className="prose-invert mt-6 flex flex-col gap-4 text-sm leading-relaxed text-slate-300 [&_a]:text-radiant [&_a]:underline [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-bold [&_h2]:text-white">
          {children}
        </div>
        <nav className="mt-10 flex flex-wrap gap-4 border-t border-base-800 pt-4 text-xs text-slate-500">
          <Link href="/privacy" className="hover:text-radiant">
            {t('privacy')}
          </Link>
          <Link href="/terms" className="hover:text-radiant">
            {t('terms')}
          </Link>
          <Link href="/refund" className="hover:text-radiant">
            {t('refund')}
          </Link>
          <a href={`mailto:${SUPPORT_EMAIL}`} className="hover:text-radiant">
            {SUPPORT_EMAIL}
          </a>
        </nav>
      </main>
    </div>
  );
}
