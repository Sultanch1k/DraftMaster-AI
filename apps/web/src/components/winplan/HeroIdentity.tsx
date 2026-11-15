'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { cdn } from '@/lib/format';
import type { WinPlanView } from '@/lib/winplan';
import { HeroPortrait } from '../HeroPortrait';

/**
 * Hero Identity header — the protagonist of the dossier.
 *
 * Cinematic hero artwork under a controlled scrim, the hero name in editorial
 * display type, and the draft verdict. Artwork supports the content: the scrim
 * keeps every piece of text legible and nothing important sits over the busy
 * centre of the portrait.
 */
export function WinPlanHeroIdentity({ plan }: { plan: WinPlanView }) {
  const t = useTranslations('winplan');
  const [artFailed, setArtFailed] = useState(false);
  const art = plan.heroArt ? cdn(plan.heroArt) : '';
  const showArt = Boolean(art) && !artFailed;

  return (
    <section className="relative overflow-hidden rounded-panel border border-base-700 bg-base-900">
      {showArt && (
        <div className="pointer-events-none absolute inset-0" aria-hidden>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={art}
            alt=""
            className="h-full w-full object-cover object-[center_22%]"
            loading="eager"
            decoding="async"
            onError={() => setArtFailed(true)}
          />
          <div className="absolute inset-0 scrim" />
        </div>
      )}

      <div className="relative flex min-h-[248px] flex-col justify-end gap-4 p-5 sm:min-h-[300px] sm:p-7">
        <span className="kicker">{plan.mode === 'counter' ? t('mode.counter') : t('mode.strategy')}</span>

        <div className="flex items-end gap-4">
          <span className="hidden sm:block">
            <HeroPortrait icon={plan.heroIcon} name={plan.heroName} size={84} priority className="ring-1 ring-white/10" />
          </span>
          <div className="min-w-0 flex-1">
            <h1 className="display truncate text-4xl leading-[0.95] text-ink sm:text-5xl xl:text-6xl">{plan.heroName}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              {plan.role && <span className="chip">{t('roleLabel', { role: plan.role })}</span>}
              {plan.lane && <span className="chip">{plan.lane}</span>}
              {plan.roles.slice(0, 3).map((r) => (
                <span key={r} className="chip border-base-600/60 text-ink-faint">
                  {r}
                </span>
              ))}
              {plan.patch && <span className="chip border-base-600/60 text-ink-faint">{t('patch', { patch: plan.patch })}</span>}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/**
 * The one-sentence win plan — the strongest typographic hook after the hero name.
 */
export function WinPlanStatement({ sentence }: { sentence: string }) {
  const t = useTranslations('winplan');
  return (
    <section className="relative overflow-hidden rounded-panel border border-accent/40 bg-gradient-to-br from-accent/10 via-base-850 to-base-850 p-5 sm:p-6">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-accent/10 blur-3xl" aria-hidden />
      <p className="kicker relative mb-2">{t('mainPlan')}</p>
      <p className="display relative text-xl leading-snug text-ink sm:text-2xl xl:text-[28px]">{sentence}</p>
    </section>
  );
}
