'use client';

import { useMemo } from 'react';
import { ArrowRight, Shield, Swords } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cdn } from '@/lib/format';
import { heroArt } from '@/lib/heroes';

/**
 * Cinematic opening band — the first thing a visitor sees.
 *
 * Rather than a dashboard card, the product opens like a strategy codex: a
 * montage of hero artwork under a heavy scrim, an editorial headline, and the
 * two analysis modes as first-class choices. The mode cards are the primary
 * navigation into the product, so a newcomer knows exactly where to start.
 */
const ART_IDS = [74, 8, 5, 2, 76, 25]; // Invoker, Juggernaut, Crystal Maiden, Axe, Sniper, Lion

export function HomeHero({
  mode,
  onCounter,
  onStrategy,
  patch,
  heroCount,
}: {
  mode: 'counter' | 'strategy' | null;
  onCounter: () => void;
  onStrategy: () => void;
  patch?: string | null;
  heroCount: number;
}) {
  const t = useTranslations('home');
  const art = useMemo(
    () =>
      ART_IDS.map((id) => heroArt(id))
        .filter(Boolean)
        .map((p) => cdn(p)),
    [],
  );

  return (
    <section className="relative overflow-hidden rounded-panel border border-base-700 bg-base-950">
      {/* Hero artwork montage. Decorative only; every caption sits on the scrim. */}
      <div className="pointer-events-none absolute inset-0" aria-hidden>
        <div className="absolute inset-0 flex">
          {art.map((src, i) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              key={src}
              src={src}
              alt=""
              className="h-full min-w-0 flex-1 object-cover object-[center_18%] opacity-[0.55]"
              style={{ objectPosition: `${20 + i * 12}% 20%` }}
              loading={i < 2 ? 'eager' : 'lazy'}
              decoding="async"
            />
          ))}
        </div>
        <div className="absolute inset-0 scrim" />
        <div className="absolute inset-0 bg-gradient-to-r from-base-950 via-base-950/70 to-transparent" />
      </div>

      <div className="relative flex flex-col gap-8 p-5 sm:p-8 xl:p-10">
        <div className="max-w-3xl">
          <span className="kicker">{t('kicker')}</span>
          <h1 className="display mt-3 text-4xl leading-[0.98] text-ink sm:text-5xl xl:text-6xl">
            {t('headline1')}
            <span className="block text-accent-bright">{t('headline2')}</span>
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-relaxed text-ink-soft sm:text-base">
            {t('sub')}
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-2">
            <span className="chip border-base-600/70">{t('patch', { patch: patch || '—' })}</span>
            <span className="chip border-base-600/70">{t('heroes', { count: heroCount || 127 })}</span>
            <span className="chip border-base-600/70">{t('data')}</span>
          </div>
        </div>

        {/* The two analysis modes, as first-class, equal-weight choices. */}
        <div className="grid gap-3 sm:grid-cols-2">
          <ModeCard
            accent="dire"
            active={mode === 'counter'}
            icon={<Swords className="h-5 w-5" />}
            title={t('counterTitle')}
            body={t('counterBody')}
            cta={t('counterCta')}
            onClick={onCounter}
          />
          <ModeCard
            accent="radiant"
            active={mode === 'strategy'}
            icon={<Shield className="h-5 w-5" />}
            title={t('strategyTitle')}
            body={t('strategyBody')}
            cta={t('strategyCta')}
            onClick={onStrategy}
          />
        </div>
      </div>
    </section>
  );
}

function ModeCard({
  accent,
  active,
  icon,
  title,
  body,
  cta,
  onClick,
}: {
  accent: 'dire' | 'radiant';
  active: boolean;
  icon: React.ReactNode;
  title: string;
  body: string;
  cta: string;
  onClick: () => void;
}) {
  const ring = accent === 'dire' ? 'hover:border-dire/70 focus-visible:ring-dire/60' : 'hover:border-radiant/70 focus-visible:ring-radiant/60';
  const badge = accent === 'dire' ? 'bg-dire/15 text-dire' : 'bg-radiant/15 text-radiant';
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`group flex flex-col items-start gap-3 rounded-panel border bg-base-900/70 p-4 text-left backdrop-blur-sm transition focus:outline-none focus-visible:ring-2 sm:p-5 ${
        active ? 'border-accent/60' : 'border-base-700'
      } ${ring}`}
    >
      <span className={`flex h-11 w-11 items-center justify-center rounded-xl ${badge}`}>{icon}</span>
      <span className="text-base font-black text-ink sm:text-lg">{title}</span>
      <span className="text-xs leading-relaxed text-ink-muted sm:text-sm">{body}</span>
      <span className="mt-auto inline-flex items-center gap-1.5 pt-1 text-sm font-bold text-accent-bright">
        {cta}
        <ArrowRight className="h-4 w-4 transition group-hover:translate-x-0.5" />
      </span>
    </button>
  );
}
