import type { Metadata } from 'next';
import Link from 'next/link';
import { getTranslations } from 'next-intl/server';
import { SeoHeader } from '@/components/SeoHeader';
import { slugForName } from '@/lib/heroes';
import type { Meta } from '@/lib/types';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';
const API = (process.env.API_PROXY_TARGET || 'http://127.0.0.1:12001').replace(/\/$/, '');

/** Rebuild hourly: the meta moves on a patch cadence, not by the minute. */
export const revalidate = 3600;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('metaPage');
  const title = t('title');
  const description = t('description');
  return {
    title,
    description,
    alternates: { canonical: '/meta' },
    openGraph: { title, description, url: `${BASE}/meta`, type: 'article' },
    twitter: { card: 'summary', title, description },
  };
}

async function loadMeta(): Promise<Meta | null> {
  try {
    const res = await fetch(`${API}/api/meta`, { next: { revalidate } });
    if (!res.ok) return null;
    return (await res.json()) as Meta;
  } catch {
    return null;
  }
}

function HeroRow({ name, value, sub, tone }: { name: string; value: string; sub: string; tone: string }) {
  const slug = slugForName(name);
  const inner = (
    <>
      <span className="flex-1 text-sm font-semibold text-slate-200">{name}</span>
      <span className={`tabular-nums text-sm font-bold ${tone}`}>{value}</span>
      <span className="w-20 text-right text-[10px] uppercase tracking-wide text-slate-500">{sub}</span>
    </>
  );
  return (
    <li>
      {slug ? (
        <Link href={`/hero/${slug}`} className="flex items-center gap-3 rounded-lg border border-base-800 bg-base-900/50 p-2 hover:border-radiant/40">
          {inner}
        </Link>
      ) : (
        <div className="flex items-center gap-3 rounded-lg border border-base-800 bg-base-900/50 p-2">{inner}</div>
      )}
    </li>
  );
}

/**
 * Meta Intelligence — the patch-winners / patch-losers surface.
 *
 * This is the page the growth content links to, and it targets a real query
 * ("dota 2 patch winners", "best heroes this patch") that spikes after every
 * patch. It is rendered from live OpenDota-derived data, not a static article,
 * so it stays correct without anyone editing it.
 */
export default async function MetaPage() {
  const t = await getTranslations('metaPage');
  const meta = await loadMeta();

  return (
    <div className="min-h-dvh">
      <SeoHeader />
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6">
        <section>
          <h1 className="text-2xl font-black text-white sm:text-3xl">{t('title')}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">
            {meta ? t('intro', { patch: meta.patch ?? '', source: meta.source }) : t('unavailable')}
          </p>
        </section>

        {meta && (
          <div className="grid gap-4 lg:grid-cols-3">
            <section className="card card-pad">
              <h2 className="section-title mb-3">🔥 {t('trending')}</h2>
              <ul className="flex flex-col gap-1.5">
                {meta.trending.slice(0, 10).map((row) => (
                  <HeroRow key={row.hero_id} name={row.hero} value={row.picks.toLocaleString('en-US')} sub={t('picks')} tone="text-slate-200" />
                ))}
              </ul>
            </section>
            <section className="card card-pad">
              <h2 className="section-title mb-3 text-radiant">📈 {t('winners')}</h2>
              <ul className="flex flex-col gap-1.5">
                {meta.patch_winners.slice(0, 10).map((row) => (
                  <HeroRow key={row.hero_id} name={row.hero} value={`${(row.cm_winrate * 100).toFixed(1)}%`} sub={t('cmWinrate')} tone="text-radiant" />
                ))}
              </ul>
            </section>
            <section className="card card-pad">
              <h2 className="section-title mb-3 text-dire">📉 {t('losers')}</h2>
              <ul className="flex flex-col gap-1.5">
                {meta.patch_losers.slice(0, 10).map((row) => (
                  <HeroRow key={row.hero_id} name={row.hero} value={`${(row.cm_winrate * 100).toFixed(1)}%`} sub={t('cmWinrate')} tone="text-dire" />
                ))}
              </ul>
            </section>
          </div>
        )}
        <section className="card card-pad flex flex-col items-start gap-3 bg-radiant/5">
          <h2 className="text-lg font-black text-white">{t('ctaTitle')}</h2>
          <p className="max-w-2xl text-sm text-slate-400">{t('ctaBody')}</p>
          <Link href="/" className="btn-primary">
            {t('cta')}
          </Link>
        </section>
      </main>
    </div>
  );
}
