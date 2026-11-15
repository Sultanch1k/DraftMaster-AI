'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Layers, ListOrdered, Loader2, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import type { Report } from '@/lib/types';
import { cn, rankLabelToTier } from '@/lib/format';
import { fromReport } from '@/lib/winplan';
import { Card } from './Card';
import { BestHeroCard } from './ReportCards';
import { WinPlanView } from './winplan/WinPlanView';

/**
 * Full counter-pick report.
 *
 * The result is assembled from the shared Win Plan system (hero identity, verdict,
 * win condition, statement, why, kill priority, danger, items, spikes, phases,
 * threats, mistakes). Two things are specific to this mode and stay here:
 *   1. the Top-5 pick selector — the counter-pick decision that drives the plan,
 *   2. the skill build and talent tree — hero mechanics, not draft strategy.
 *
 * Every hero in the Top 5 is selectable; clicking one swaps the whole plan in
 * place while the pick list stays stable so the user keeps their bearings.
 */
export function ReportView({ report: incoming }: { report: Report }) {
  const t = useTranslations('report');
  const [report, setReport] = useState(incoming);
  const [activeHeroId, setActiveHeroId] = useState<number | null>(incoming.best_picks[0]?.hero_id ?? null);
  const [switching, setSwitching] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReport(incoming);
    setActiveHeroId(incoming.best_picks[0]?.hero_id ?? null);
    setSwitching(null);
    setError(null);
  }, [incoming]);

  const enemyIds = useMemo(() => report.enemy_draft.map((h) => h.id), [report.enemy_draft]);

  const selectHero = useCallback(
    async (heroId: number) => {
      if (heroId === activeHeroId || switching !== null) return;
      setError(null);

      // Every Top-5 candidate ships with its own precomputed report, so switching
      // is instant and costs no extra quota. Fall back to a fresh request only for
      // heroes that were not precomputed (manual picks, screenshot detections).
      const precomputed = report.pick_reports?.[String(heroId)];
      if (precomputed) {
        setReport({ ...precomputed, best_picks: report.best_picks, pick_reports: report.pick_reports });
        setActiveHeroId(heroId);
        return;
      }

      setSwitching(heroId);
      try {
        const res = await api.analyse(enemyIds, heroId, report.role ?? undefined, rankLabelToTier(report.rank));
        setReport({ ...res.report, best_picks: report.best_picks, pick_reports: report.pick_reports });
        setActiveHeroId(heroId);
      } catch (e) {
        setError((e as ApiError).message ?? t('loading'));
      } finally {
        setSwitching(null);
      }
    },
    [activeHeroId, enemyIds, report.best_picks, report.pick_reports, report.rank, report.role, switching, t],
  );

  const plan = useMemo(() => fromReport(report), [report]);
  const sb = report.skill_build;
  const talents = report.talents ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Card
        title={t('s1')}
        icon={<ListOrdered className="h-4 w-4 text-accent" />}
        action={<span className="chip hidden sm:inline-flex">{t('s1Chip')}</span>}
      >
        <div className="grid gap-3 xl:grid-cols-2">
          {report.best_picks.map((p, i) => (
            <BestHeroCard
              key={p.hero_id}
              pick={p}
              rank={i + 1}
              selected={p.hero_id === activeHeroId}
              loading={switching === p.hero_id}
              onSelect={() => selectHero(p.hero_id)}
            />
          ))}
        </div>
        {switching !== null && <Loader2 className="mt-3 h-4 w-4 animate-spin text-accent" />}
        {error && <p className="mt-3 rounded-lg border border-dire/50 bg-dire/10 p-2.5 text-sm text-dire">{error}</p>}
      </Card>

      <WinPlanView plan={plan} />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title={`5 · ${t('s5')}`} icon={<Layers className="h-4 w-4 text-magic" />}>
          <div className="flex flex-wrap gap-1">
            {sb.levels.map((l) => (
              <span
                key={l.level}
                title={`${t('level', { level: l.level })} · ${l.choice} — ${l.reason}`}
                className={cn(
                  'flex h-8 w-8 flex-col items-center justify-center rounded-md border text-[10px] font-bold leading-none',
                  l.kind === 'ultimate' && 'border-gold/60 bg-gold/15 text-gold',
                  l.kind === 'talent' && 'border-magic/60 bg-magic/15 text-magic',
                  l.kind === 'stats' && 'border-base-600 bg-base-800 text-ink-faint',
                  l.kind === 'basic' && 'border-base-600 bg-base-850 text-ink-soft',
                )}
              >
                <span className="text-[8px] opacity-60">{l.level}</span>
                {l.kind === 'basic'
                  ? l.choice
                      .split(' ')
                      .map((w) => w[0])
                      .join('')
                      .slice(0, 3)
                  : l.kind === 'ultimate'
                    ? 'ULT'
                    : l.kind === 'talent'
                      ? 'TAL'
                      : 'STAT'}
              </span>
            ))}
          </div>
          <p className="mt-3 flex flex-wrap gap-x-1.5 text-xs text-ink-muted">
            <span className="font-semibold text-radiant">{sb.primary}</span>
            <span>{t('maxedFirstSuffix')}</span>
            <span className="font-semibold text-ink-soft">{sb.secondary}</span>
            <span>{t('secondSuffix')}</span>
            {sb.ultimate && (
              <>
                <span className="font-semibold text-gold">{sb.ultimate}</span>
                <span>{t('ultimateSuffix')}</span>
              </>
            )}
          </p>
          {sb.notes.length > 0 && (
            <ul className="mt-3 flex flex-col gap-1.5">
              {sb.notes.map((n, i) => (
                <li key={i} className="rounded-md border border-base-700 bg-base-900/50 px-2.5 py-1.5 text-[11px] text-ink-muted">
                  {n}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={`6 · ${t('s6')}`} icon={<Sparkles className="h-4 w-4 text-magic" />}>
          {talents.length === 0 ? (
            <p className="text-sm text-ink-faint">{t('noTalentData')}</p>
          ) : (
            <ul className="flex flex-col gap-2.5">
              {talents.map((tal) => (
                <li key={tal.hero_level} className="rounded-lg border border-base-700 bg-base-900/50 p-2.5">
                  <p className="label mb-1 text-magic">{t('level', { level: tal.hero_level })}</p>
                  <p className="text-sm font-semibold text-ink">{tal.recommended}</p>
                  <p className="mt-0.5 text-[11px] text-ink-muted">
                    {t('alternative', { options: tal.options.filter((o) => o !== tal.recommended).join(' / ') || '—' })}
                  </p>
                  <p className="mt-1 text-[11px] italic text-ink-faint">{tal.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <p className="pb-2 text-center text-[11px] text-ink-faint">
        {t('footer', { patch: report.patch ?? '—', ms: report.generated_in_ms })}
      </p>
    </div>
  );
}
