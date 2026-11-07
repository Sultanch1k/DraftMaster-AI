'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpen, Clock, Layers, ListOrdered, Loader2, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import type { Report } from '@/lib/types';
import { cn, rankLabelToTier } from '@/lib/format';
import { Card } from './Card';
import { HeroPortrait } from './HeroPortrait';
import {
  BestHeroCard,
  ItemBuildCard,
  OneSentencePlan,
  PowerSpikeCard,
  TargetPriorityCard,
  ThreatCard,
  WinConditionsCard,
} from './ReportCards';
import { WinProbabilityBar, WinProbFactors } from './WinProbability';

/**
 * Full 11-section report.
 *
 * Every hero in the Top 5 is selectable: clicking a card fetches that hero's own
 * report and swaps the whole analysis in place, while the pick list stays stable
 * so the user keeps their bearings while comparing options.
 */
export function ReportView({ report: incoming }: { report: Report }) {
  const t = useTranslations('report');
  const tFields = useTranslations('fields');
  const [report, setReport] = useState(incoming);
  const [activeHeroId, setActiveHeroId] = useState<number | null>(incoming.best_picks[0]?.hero_id ?? null);
  const [switching, setSwitching] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A new draft (or a new screenshot) resets the view to its own #1 pick.
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
      setSwitching(heroId);
      setError(null);
      try {
        const res = await api.analyse(enemyIds, heroId, report.role ?? undefined, rankLabelToTier(report.rank));
        // Keep the original Top 5 ordering so cards do not jump around.
        setReport({ ...res.report, best_picks: report.best_picks });
        setActiveHeroId(heroId);
      } catch (e) {
        setError((e as ApiError).message ?? t('loading'));
      } finally {
        setSwitching(null);
      }
    },
    [activeHeroId, enemyIds, report.best_picks, report.rank, report.role, switching, t],
  );

  const activePick = report.best_picks.find((p) => p.hero_id === activeHeroId) ?? report.best_picks[0];
  const sb = report.skill_build;
  const talents = report.talents ?? [];

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <div className="grid gap-6 xl:grid-cols-[1fr_1.15fr]">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              {report.draft_summary.hero && (
                <HeroPortrait icon={activePick?.icon ?? null} name={report.draft_summary.hero} size={56} priority />
              )}
              <div className="min-w-0">
                <p className="label">{t('analysedPick')}</p>
                <h2 className="text-xl font-black text-white sm:text-2xl">{report.draft_summary.hero ?? '—'}</h2>
                <p className="text-xs text-slate-400">
                  {t('vs', { heroes: report.enemy_draft.map((h) => h.localized_name).join(', ') })}
                </p>
              </div>
              {switching !== null && <Loader2 className="ml-auto h-4 w-4 animate-spin text-radiant" />}
            </div>
            <OneSentencePlan sentence={report.one_sentence_win_plan} label={t('s11')} />
            <div className="flex flex-wrap gap-2">
              {report.draft_summary.headline_threats.map((th) => (
                <span
                  key={th.dimension}
                  className={cn(
                    'chip',
                    th.danger === 'high' && 'border-dire/50 text-dire',
                    th.danger === 'medium' && 'border-gold/50 text-gold',
                    th.danger === 'low' && 'border-radiant/50 text-radiant',
                  )}
                >
                  {th.dimension} {th.score.toFixed(0)}
                </span>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <WinProbabilityBar wp={report.win_probability} />
            <WinProbFactors wp={report.win_probability} />
          </div>
        </div>
      </Card>

      <Card
        title={`1 · ${t('s1')}`}
        icon={<ListOrdered className="h-4 w-4 text-radiant" />}
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
        {error && <p className="mt-3 rounded-lg border border-dire/50 bg-dire/10 p-2.5 text-sm text-dire">{error}</p>}
      </Card>

      <Card title={`2 · ${t('s2')}`} icon={<BookOpen className="h-4 w-4 text-radiant" />}>
        <ul className="flex flex-col gap-2">
          {report.why_this_hero.map((line, i) => (
            <li key={i} className="flex gap-2 text-sm leading-relaxed text-slate-200">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-radiant" />
              {line}
            </li>
          ))}
        </ul>
        {activePick?.strong_against?.length ? (
          <div className="mt-3 rounded-lg border border-base-700 bg-base-900/50 p-3">
            <p className="label mb-1.5">{t('strongInto')}</p>
            <div className="flex flex-wrap gap-2">
              {activePick.strong_against.slice(0, 6).map((name) => (
                <span key={name} className="chip border-radiant/40 text-radiant">
                  {name}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </Card>

      <div>
        <SectionHeading n={3} title={t('s3')} />
        <ThreatCard analysis={report.threat_analysis} />
      </div>

      <div>
        <SectionHeading n={4} title={t('s4')} />
        <ItemBuildCard build={report.item_build} />
      </div>

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
                  l.kind === 'stats' && 'border-base-600 bg-base-800 text-slate-400',
                  l.kind === 'basic' && 'border-base-600 bg-base-850 text-slate-200',
                )}
              >
                <span className="text-[8px] opacity-60">{l.level}</span>
                {l.kind === 'basic'
                  ? l.choice.split(' ').map((w) => w[0]).join('').slice(0, 3)
                  : l.kind === 'ultimate'
                    ? 'ULT'
                    : l.kind === 'talent'
                      ? 'TAL'
                      : 'STAT'}
              </span>
            ))}
          </div>
          <p className="mt-3 flex flex-wrap gap-x-1.5 text-xs text-slate-400">
            <span className="font-semibold text-radiant">{sb.primary}</span>
            <span>{t('maxedFirstSuffix')}</span>
            <span className="font-semibold text-slate-300">{sb.secondary}</span>
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
                <li key={i} className="rounded-md border border-base-700 bg-base-900/50 px-2.5 py-1.5 text-[11px] text-slate-300">
                  {n}
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title={`6 · ${t('s6')}`} icon={<Sparkles className="h-4 w-4 text-magic" />}>
          {talents.length === 0 ? (
            <p className="text-sm text-slate-500">{t('noTalentData')}</p>
          ) : (
            <ul className="flex flex-col gap-2.5">
              {talents.map((tal) => (
                <li key={tal.hero_level} className="rounded-lg border border-base-700 bg-base-850/60 p-2.5">
                  <p className="label mb-1 text-magic">{t('level', { level: tal.hero_level })}</p>
                  <p className="text-sm font-semibold text-white">{tal.recommended}</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    {t('alternative', { options: tal.options.filter((o) => o !== tal.recommended).join(' / ') || '—' })}
                  </p>
                  <p className="mt-1 text-[11px] italic text-slate-500">{tal.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title={`7 · ${t('s7')}`} icon={<Clock className="h-4 w-4 text-gold" />}>
        <div className="flex flex-col gap-2.5">
          {report.match_plan.map((p) => (
            <div key={p.window} className="rounded-lg border border-base-700 bg-base-850/60 p-3">
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-bold text-gold">
                  {t('min', { window: p.window })}
                </span>
                <span className="text-sm font-bold text-white">{p.phase}</span>
              </div>
              <div className="grid gap-2 text-xs sm:grid-cols-2 xl:grid-cols-3">
                <Field label={tFields('objectives')} value={p.objectives} />
                <Field label={tFields('farmFocus')} value={p.farm_focus} />
                <Field label={tFields('fightFocus')} value={p.fight_focus} />
                <Field label={tFields('mapMovement')} value={p.map_movement} />
                <Field label={tFields('towerPriority')} value={p.tower_priority} />
                <Field label={tFields('roshanPriority')} value={p.roshan_priority} />
                <Field label={tFields('dangerZones')} value={p.danger_zones} tone="danger" />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 xl:grid-cols-2">
        <div>
          <SectionHeading n={8} title={t('s8')} />
          <WinConditionsCard conditions={report.win_conditions} />
        </div>
        <div>
          <SectionHeading n={9} title={t('s9')} />
          <TargetPriorityCard targets={report.target_priority} />
        </div>
      </div>

      <div>
        <SectionHeading n={10} title={t('s10')} />
        <PowerSpikeCard spikes={report.power_spikes} />
      </div>

      <div>
        <SectionHeading n={11} title={t('s11')} />
        <OneSentencePlan sentence={report.one_sentence_win_plan} label={t('finalTakeaway')} />
      </div>

      <p className="pb-2 text-center text-[11px] text-slate-600">
        {t('footer', { patch: report.patch ?? '—', ms: report.generated_in_ms })}
      </p>
    </div>
  );
}

function SectionHeading({ n, title }: { n: number; title: string }) {
  return (
    <h2 className="mb-2 flex items-center gap-2 px-1 text-sm font-bold uppercase tracking-wider text-slate-400">
      <span className="flex h-5 w-5 items-center justify-center rounded bg-base-700 text-[11px] text-slate-300">{n}</span>
      {title}
    </h2>
  );
}

function Field({ label, value, tone }: { label: string; value: string | string[]; tone?: 'danger' }) {
  const text = Array.isArray(value) ? value.join(' · ') : value;
  return (
    <div>
      <p className={cn('label mb-0.5', tone === 'danger' && 'text-dire')}>{label}</p>
      <p className={cn('leading-relaxed text-slate-300', tone === 'danger' && 'text-slate-400')}>{text}</p>
    </div>
  );
}
