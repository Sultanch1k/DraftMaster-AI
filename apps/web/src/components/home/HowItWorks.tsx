'use client';

import { Crosshair, ListChecks, Timer, Trophy } from 'lucide-react';
import { useTranslations } from 'next-intl';

/**
 * "How it works" strip.
 *
 * A first-time visitor needs to know the product produces a *game plan*, not a
 * hero pick, within seconds of landing. Four short steps state the promise and
 * the outputs, so the value is legible before any interaction.
 */
const STEPS = [
  { key: 'step1', icon: Crosshair },
  { key: 'step2', icon: ListChecks },
  { key: 'step3', icon: Timer },
  { key: 'step4', icon: Trophy },
] as const;

export function HowItWorks() {
  const t = useTranslations('home.steps');
  return (
    <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {STEPS.map(({ key, icon: Icon }, i) => (
        <div key={key} className="card card-pad flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-base-800 text-accent-bright">
              <Icon className="h-4 w-4" />
            </span>
            <span className="tabular text-xs font-bold text-ink-faint">{String(i + 1).padStart(2, '0')}</span>
          </div>
          <h3 className="text-sm font-bold text-ink">{t(`${key}Title`)}</h3>
          <p className="text-xs leading-relaxed text-ink-muted">{t(`${key}Body`)}</p>
        </div>
      ))}
    </section>
  );
}
