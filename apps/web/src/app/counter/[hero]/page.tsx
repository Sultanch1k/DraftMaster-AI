import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getTranslations } from 'next-intl/server';
import { HeroPortrait } from '@/components/HeroPortrait';
import { allSeoHeroes, getSeoHero, SEO_PATCH } from '@/lib/seo';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export function generateStaticParams() {
  return allSeoHeroes.map((h) => ({ hero: h.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ hero: string }> }): Promise<Metadata> {
  const { hero: slug } = await params;
  const hero = getSeoHero(slug);
  if (!hero) return {};
  const title = `What Counters ${hero.name}? Best ${hero.name} Counters & Items`.trim();
  const description = `The ${hero.counters.length} best ${hero.name} counters in Dota 2, ranked by real match data, plus the items to buy and avoid against ${hero.name}. Updated for patch ${SEO_PATCH}.`;
  return {
    title,
    description,
    alternates: { canonical: `/counter/${hero.slug}` },
    openGraph: { title, description, url: `${BASE}/counter/${hero.slug}`, type: 'article' },
    twitter: { card: 'summary', title, description },
  };
}

export default async function CounterPage({ params }: { params: Promise<{ hero: string }> }) {
  const { hero: slug } = await params;
  const hero = getSeoHero(slug);
  if (!hero) notFound();
  const t = await getTranslations('seo');

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: `What counters ${hero.name} in Dota 2?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: `The strongest counters to ${hero.name} are ${hero.counters
            .slice(0, 5)
            .map((c) => c.name)
            .join(', ')}, based on ${SEO_PATCH} match data.`,
        },
      },
      {
        '@type': 'Question',
        name: `What items should you buy against ${hero.name}?`,
        acceptedAnswer: {
          '@type': 'Answer',
          text: hero.good_items.length
            ? `Against ${hero.name} consider ${hero.good_items.map((i) => i.name).join(', ')}.`
            : `Item choices against ${hero.name} depend on your role and build.`,
        },
      },
    ],
  };

  return (
    <div className="min-h-dvh">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

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

      <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6">
        <section className="flex flex-col items-start gap-4 sm:flex-row sm:items-center">
          <HeroPortrait icon={hero.icon} name={hero.name} size={72} priority />
          <div>
            <h1 className="text-2xl font-black text-white sm:text-3xl">{t('h1', { hero: hero.name })}</h1>
            <p className="mt-1 max-w-2xl text-sm text-slate-400">
              {t('intro', { hero: hero.name, patch: SEO_PATCH ?? '' })}
            </p>
            <p className="mt-1 text-xs text-slate-500">{t('winrate', { hero: hero.name, winrate: hero.pub_winrate.toFixed(1) })}</p>
          </div>
        </section>

        <section className="card card-pad">
          <h2 className="section-title">{t('countersTitle', { hero: hero.name })}</h2>
          <p className="mb-3 text-xs text-slate-500">{t('countersSub')}</p>
          <ol className="grid gap-2 sm:grid-cols-2">
            {hero.counters.map((c, i) => (
              <li key={c.id}>
                <Link
                  href={`/counter/${c.slug}`}
                  className="flex items-center gap-3 rounded-lg border border-base-800 bg-base-900/50 p-2 transition-colors hover:border-radiant/40"
                >
                  <span className="w-5 text-center text-xs font-bold text-slate-500">{i + 1}</span>
                  <HeroPortrait icon={null} name={c.name} size={32} />
                  <span className="flex-1 text-sm font-semibold text-slate-200">{c.name}</span>
                  <span className="chip border-radiant/40 text-radiant">
                    {c.score >= 0 ? `+${(c.score * 100).toFixed(1)}` : (c.score * 100).toFixed(1)}
                  </span>
                </Link>
              </li>
            ))}
          </ol>
        </section>

        <section className="card card-pad">
          <h2 className="section-title">{t('goodVsTitle', { hero: hero.name })}</h2>
          <p className="mb-3 text-xs text-slate-500">{t('itemsSub')}</p>
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
          {hero.bad_items.length > 0 && (
            <>
              <h3 className="mt-4 text-xs font-bold uppercase tracking-wide text-slate-400">{t('avoidTitle')}</h3>
              <ul className="mt-2 flex flex-wrap gap-2">
                {hero.bad_items.map((it) => (
                  <li key={it.key} className="chip border-dire/40 text-slate-300 line-through decoration-dire/60">
                    {it.name}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="card card-pad">
          <h2 className="section-title">{t('strongTitle', { hero: hero.name })}</h2>
          <ul className="flex flex-wrap gap-2">
            {hero.strong_against.map((c) => (
              <li key={c.id}>
                <Link href={`/counter/${c.slug}`} className="chip border-base-700 text-slate-300 hover:border-radiant/40">
                  {c.name}
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="card card-pad flex flex-col items-start gap-3 bg-radiant/5">
          <h2 className="text-lg font-black text-white">{t('ctaTitle', { hero: hero.name })}</h2>
          <Link href="/" className="btn-primary">
            {t('cta')}
          </Link>
        </section>

        <nav aria-label={t('allHeroes')} className="flex flex-wrap gap-2">
          {allSeoHeroes.slice(0, 60).map((h) => (
            <Link key={h.slug} href={`/counter/${h.slug}`} className="text-[11px] text-slate-500 hover:text-radiant">
              {h.name}
            </Link>
          ))}
        </nav>
      </main>
    </div>
  );
}
