import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getTranslations } from 'next-intl/server';
import { HeroPortrait } from '@/components/HeroPortrait';
import { SeoHeader } from '@/components/SeoHeader';
import { allSeoHeroes, getSeoHero, SEO_PATCH } from '@/lib/seo';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

/**
 * Per-hero guide page — the landing surface for "how to play X" searches.
 *
 * Every number here is the same one the engine uses, so the page can never
 * disagree with the product. The page's job is to answer the query and then
 * hand the reader the interactive tool.
 */
export function generateStaticParams() {
  return allSeoHeroes.map((h) => ({ hero: h.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ hero: string }> }): Promise<Metadata> {
  const { hero: slug } = await params;
  const hero = getSeoHero(slug);
  if (!hero) return {};
  const title = `How to Play ${hero.name} in Dota 2 — Build, Items & Matchups`;
  const description = `How to play ${hero.name} on patch ${SEO_PATCH}: win rate, the heroes to fear, the items that answer them, and the exact game plan for your enemy draft.`;
  return {
    title,
    description,
    alternates: { canonical: `/hero/${hero.slug}` },
    openGraph: { title, description, url: `${BASE}/hero/${hero.slug}`, type: 'article' },
    twitter: { card: 'summary', title, description },
  };
}

export default async function HeroGuidePage({ params }: { params: Promise<{ hero: string }> }) {
  const { hero: slug } = await params;
  const hero = getSeoHero(slug);
  if (!hero) notFound();
  const t = await getTranslations('guide');

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: `What is ${hero.name}'s win rate in Dota 2?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `${hero.name} wins ${hero.pub_winrate.toFixed(1)}% of public games and ${hero.cm_winrate.toFixed(1)}% of Captain's Mode games on patch ${SEO_PATCH}.`,
        },
      },
      {
        '@type': 'Question',
        name: `What counters ${hero.name}?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `The strongest counters are ${hero.counters.slice(0, 5).map((c) => c.name).join(', ')}.`,
        },
      },
    ],
  };

  return (
    <div className="min-h-dvh">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <SeoHeader />

      <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6">
        <section className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <HeroPortrait icon={hero.icon} name={hero.name} size={72} priority />
          <div>
            <h1 className="text-2xl font-black text-white sm:text-3xl">{t('h1', { hero: hero.name })}</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">{t('intro', { hero: hero.name, patch: SEO_PATCH ?? '' })}</p>
            <p className="mt-1 text-xs text-slate-500">
              {t('winrates', {
                pub: hero.pub_winrate.toFixed(1),
                cm: hero.cm_winrate.toFixed(1),
              })}
            </p>
            <p className="mt-1 text-xs text-slate-500">{t('roles')}: {hero.roles.join(' · ')}</p>
          </div>
        </section>

        <section className="card card-pad">
          <h2 className="section-title">{t('fearTitle', { hero: hero.name })}</h2>
          <p className="mb-3 text-xs text-slate-500">{t('fearSub', { hero: hero.name })}</p>
          <ol className="grid gap-2 sm:grid-cols-2">
            {hero.counters.slice(0, 8).map((c, i) => (
              <li key={c.id}>
                <Link
                  href={`/counter/${c.slug}`}
                  className="flex items-center gap-3 rounded-lg border border-base-800 bg-base-900/50 p-2 transition-colors hover:border-dire/40"
                >
                  <span className="w-5 text-center text-xs font-bold text-slate-500">{i + 1}</span>
                  <HeroPortrait icon={null} name={c.name} size={32} />
                  <span className="flex-1 text-sm font-semibold text-slate-200">{c.name}</span>
                  <span className="chip border-dire/40 text-dire">
                    {c.score >= 0 ? `+${(c.score * 100).toFixed(1)}` : (c.score * 100).toFixed(1)}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>

        {hero.problems.length > 0 && (
          <section className="card card-pad">
            <h2 className="section-title">{t('problemsTitle', { hero: hero.name })}</h2>
            <p className="mb-3 text-xs text-slate-500">{t('problemsSub', { hero: hero.name })}</p>
            <ul className="flex flex-wrap gap-2">
              {hero.problems.map((p) => (
                <li key={p} className="chip border-gold/40 text-gold">
                  {p}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="card card-pad">
          <h2 className="section-title">{t('itemsTitle', { hero: hero.name })}</h2>
          <p className="mb-3 text-xs text-slate-500">{t('itemsSub', { hero: hero.name })}</p>
          {hero.good_items.length ? (
            <ul className="flex flex-wrap gap-2">
              {hero.good_items.map((it) => (
                <li key={it.key} className="chip border-radiant/40 text-slate-200">
                  {it.name}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-slate-500">{t('noItems')}</p>
          )}
        </section>

        <section className="card card-pad">
          <h2 className="section-title">{t('strongTitle', { hero: hero.name })}</h2>
          <ul className="flex flex-wrap gap-2">
            {hero.strong_against.slice(0, 12).map((c) => (
              <li key={c.id}>
                <Link href={`/hero/${c.slug}`} className="chip border-base-700 text-slate-300 hover:border-radiant/40">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="card card-pad flex flex-col items-start gap-3 bg-radiant/5">
          <h2 className="text-lg font-black text-white">{t('ctaTitle', { hero: hero.name })}</h2>
          <p className="max-w-2xl text-sm text-slate-400">{t('ctaBody')}</p>
          <Link href="/" className="btn-primary">
            {t('cta')}
          </Link>
        </section>

        <nav aria-label={t('allHeroes')} className="flex flex-wrap gap-2">
          {allSeoHeroes.slice(0, 60).map((h) => (
            <Link key={h.slug} href={`/hero/${h.slug}`} className="text-[11px] text-slate-500 hover:text-radiant">
              {h.name}
            </Link>
          ))}
        </nav>
      </main>
    </div>
  );
}
