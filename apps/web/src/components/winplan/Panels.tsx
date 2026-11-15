'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/format';
import type { DraftVerdictKind, WinPlanView } from '@/lib/winplan';

const KIND_STYLE: Record<DraftVerdictKind, { text: string; bar: string; border: string }> = {
  favorable: { text: 'text-radiant', bar: 'bg-radiant', border: 'border-radiant/40' },
  competitive: { text: 'text-gold', bar: 'bg-gold', border: 'border-gold/40' },
  difficult: { text: 'text-dire', bar: 'bg-dire', border: 'border-dire/40' },
  situational: { text: 'text-steel', bar: 'bg-steel', border: 'border-steel/40' },
};

/**
 * Draft verdict.
 *
 * The categorical assessment is always shown. The numeric win probability is
 * shown only when the engine models it, and is explicitly labelled an estimate —
 * a heuristic score is never dressed up as a measured statistic.
 */
export function WinPlanVerdict({ plan }: { plan: WinPlanView }) {
  const t = useTranslations('winplan');
  const v = plan.verdict;
  const style = KIND_STYLE[v.kind];
  const hasProb = typeof v.winProbability === 'number';

  return (
    <section className={cn('rounded-panel border bg-base-850 p-4 sm:p-5', style.border)}>
      <p className="label mb-2">{t('verdict')}</p>
      <p className={cn('display text-2xl leading-none sm:text-3xl', style.text)}>{t(`verdictKind.${v.kind}`)}</p>

      {hasProb && (
        <div className="mt-4">
          <div className="flex items-end justify-between">
            <span className="text-xs text-ink-faint">{t('winProbEstimate')}</span>
            <span className={cn('tabular text-lg font-bold', style.text)}>
              {v.winProbability!.toFixed(1)}%
            </span>
          </div>
          <div className="mt-1.5 flex h-2 w-full overflow-hidden rounded-full bg-base-700">
            <div className={cn('h-full', style.bar)} style={{ width: `${Math.max(0, Math.min(100, v.winProbability!))}%` }} />
            <div className="h-full flex-1 bg-base-600" />
          </div>
          {v.confidence && <p className="mt-1.5 text-[11px] text-ink-faint">{t('confidence', { level: v.confidence })}</p>}
        </div>
      )}

      {v.assessment && <p className="mt-3 text-sm leading-relaxed text-ink-soft">{v.assessment}</p>}
    </section>
  );
}

/** Kill priority — ordered, ranked, never flat. */
export function WinPlanKillPriority({ targets }: { targets: WinPlanView['killPriority'] }) {
  const t = useTranslations('winplan');
  if (targets.length === 0) return null;
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('killPriority')}</p>
      <ol className="flex flex-col gap-2">
        {targets.map((row) => (
          <li key={row.heroId} className="flex items-center gap-3">
            <span className="tabular flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-dire/40 bg-dire/10 text-sm font-black text-dire">
              {row.rank}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-ink">{row.name}</p>
              {row.reason && <p className="truncate text-[11px] text-ink-muted">{row.reason}</p>}
            </div>
            <span className="tabular shrink-0 text-sm font-bold text-dire">{row.score.toFixed(0)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Win conditions — primary / secondary / emergency, colour-coded by tier. */
export function WinPlanWinCondition({ conditions }: { conditions: WinPlanView['winConditions'] }) {
  const t = useTranslations('winplan');
  const rows = [
    { key: 'primary', label: t('wc.primary'), value: conditions.primary, cls: 'border-radiant/40 bg-radiant/5', text: 'text-radiant' },
    { key: 'secondary', label: t('wc.secondary'), value: conditions.secondary, cls: 'border-gold/40 bg-gold/5', text: 'text-gold' },
    { key: 'emergency', label: t('wc.emergency'), value: conditions.emergency, cls: 'border-dire/40 bg-dire/5', text: 'text-dire' },
  ];
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('winCondition')}</p>
      <div className="flex flex-col gap-2.5">
        {rows.map((r) => (
          <div key={r.key} className={cn('rounded-lg border p-3', r.cls)}>
            <p className={cn('label mb-1', r.text)}>{r.label}</p>
            <p className="text-sm leading-relaxed text-ink-soft">{r.value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/** Don't-do-this — the mistakes that would break the plan. */
export function WinPlanMistakes({ mistakes }: { mistakes: string[] }) {
  const t = useTranslations('winplan');
  if (mistakes.length === 0) return null;
  return (
    <section className="rounded-panel border border-dire/35 bg-gradient-to-br from-dire/[0.07] to-base-850 p-4 sm:p-5">
      <p className="mb-3 flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.18em] text-dire">
        <span className="inline-block h-3 w-[3px] rounded-full bg-dire" aria-hidden />
        {t('dontDo')}
      </p>
      <ul className="flex flex-col gap-2">
        {mistakes.slice(0, 5).map((m, i) => (
          <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-ink-soft">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-dire" aria-hidden />
            <span>{m}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Why this hero works. */
export function WinPlanWhy({ reasons }: { reasons: string[] }) {
  const t = useTranslations('winplan');
  if (reasons.length === 0) return null;
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('whyWorks')}</p>
      <ul className="flex flex-col gap-2.5">
        {reasons.map((r, i) => (
          <li key={i} className="flex gap-3 text-sm leading-relaxed text-ink-soft">
            <span className="tabular mt-0.5 text-xs font-bold text-accent">{String(i + 1).padStart(2, '0')}</span>
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
