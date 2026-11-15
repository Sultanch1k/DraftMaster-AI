'use client';

import { Loader2, Swords } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Hero } from '@/lib/types';
import { HeroPortrait } from '../HeroPortrait';

/**
 * The command bar that turns a picked enemy draft into a plan.
 *
 * It sits directly beneath the hero grid so the two flagship actions are always
 * one thumb away from the selection, and it shows the five slots filling in as
 * the user picks — the visual feedback that makes the input feel instant.
 */
export function ActionBar({
  heroes,
  loading,
  elapsed,
  onPanic,
  onReport,
  onClear,
}: {
  heroes: Hero[];
  loading: 'panic' | 'report' | null;
  elapsed: number | null;
  onPanic: () => void;
  onReport: () => void;
  onClear: () => void;
}) {
  const t = useTranslations('hero');
  const disabled = loading !== null || heroes.length === 0;

  return (
    <section className="card card-pad">
      <div className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="label">{t('enemyDraft')}</p>
          {elapsed !== null && <span className="chip border-radiant/40 text-radiant">{t('answeredIn', { ms: elapsed })}</span>}
        </div>

        <div className="flex gap-2">
          {Array.from({ length: 5 }).map((_, i) => {
            const h = heroes[i];
            return h ? (
              <HeroPortrait key={h.id} icon={h.icon} name={h.localized_name} size={48} priority />
            ) : (
              <span
                key={`slot-${i}`}
                className="flex h-12 w-12 items-center justify-center rounded-md border border-dashed border-base-600 text-xs text-ink-faint"
              >
                {i + 1}
              </span>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={onPanic} disabled={disabled} className="btn-danger">
            {loading === 'panic' ? <Loader2 className="h-4 w-4 animate-spin" /> : <span aria-hidden>🚨</span>}
            {t('panic')}
          </button>
          <button type="button" onClick={onReport} disabled={disabled} className="btn-primary">
            {loading === 'report' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Swords className="h-4 w-4" />}
            {t('oneClick')}
          </button>
          {heroes.length > 0 && (
            <button type="button" onClick={onClear} className="btn-ghost">
              {t('clear')}
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
