import Link from 'next/link';
import { getTranslations } from 'next-intl/server';

/**
 * Minimal chrome for the public, crawlable pages (counter, hero guide, meta).
 *
 * These pages exist to be found and read by people who are not yet users, so
 * they render server-side with no app shell and a single call to action.
 */
export async function SeoHeader() {
  const t = await getTranslations('seo');
  return (
    <header className="border-b border-base-800">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="text-sm font-black tracking-tight text-white">
          DRAFT<span className="text-radiant">MASTER</span>
        </Link>
        <Link href="/" className="btn-primary text-xs">
          {t('cta')}
        </Link>
      </div>
    </header>
  );
}
