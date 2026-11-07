'use client';

import { BookOpen, Clock, Layers, ListOrdered, Sparkles } from 'lucide-react';
import type { Report } from '@/lib/types';
import { cn } from '@/lib/format';
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

export function ReportView({ report }: { report: Report }) {
  const sb = report.skill_build;
  const talents = report.talents ?? [];

  return (
    <div className="flex flex-col gap-4">
      {/* Header: verdict + win probability */}
      <Card>
        <div className="grid gap-5 lg:grid-cols-[1fr_1.1fr]">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              {report.draft_summary.hero && (
                <HeroPortrait
                  icon={report.best_picks.find((p) => p.localized_name === report.draft_summary.hero)?.icon ?? null}
                  name={report.draft_summary.hero}
                  size={52}
                  priority
                />
              )}
              <div>
                <p className="label">Analysed pick</p>
                <h2 className="text-xl font-black text-white">{report.draft_summary.hero ?? 'Draft analysis'}</h2>
                <p className="text-xs text-slate-400">
                  vs {report.enemy_draft.map((h) => h.localized_name).join(', ')}
                </p>
              </div>
            </div>
            <OneSentencePlan sentence={report.one_sentence_win_plan} />
            <div className="flex flex-wrap gap-2">
              {report.draft_summary.headline_threats.map((t) => (
                <span
                  key={t.dimension}
                  className={cn(
                    'chip',
                    t.danger === 'high' && 'border-dire/50 text-dire',
                    t.danger === 'medium' && 'border-gold/50 text-gold',
                    t.danger === 'low' && 'border-radiant/50 text-radiant',
                  )}
                >
                  {t.dimension} {t.score.toFixed(0)}
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

      {/* 1. Best picks */}
      <Card title="1 · Best Picks" icon={<ListOrdered className="h-4 w-4 text-radiant" />} action={<span className="chip">Counter · Meta · Comfort · Synergy · Role</span>}>
        <div className="grid gap-2.5 lg:grid-cols-2">
          {report.best_picks.map((p, i) => (
            <BestHeroCard key={p.hero_id} pick={p} rank={i + 1} />
          ))}
        </div>
      </Card>

      {/* 2. Why */}
      <Card title="2 · Why This Hero Works" icon={<BookOpen className="h-4 w-4 text-radiant" />}>
        <ul className="flex flex-col gap-2">
          {report.why_this_hero.map((line, i) => (
            <li key={i} className="flex gap-2 text-sm leading-relaxed text-slate-200">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-radiant" />
              {line}
            </li>
          ))}
        </ul>
        {report.best_picks[0]?.strong_against?.length ? (
          <div className="mt-3 rounded-lg border border-base-700 bg-base-900/50 p-3">
            <p className="label mb-1.5">Strong into</p>
            <div className="flex flex-wrap gap-2">
              {report.best_picks[0].strong_against.slice(0, 6).map((name) => (
                <span key={name} className="chip border-radiant/40 text-radiant">
                  {name}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </Card>

      {/* 3. Threat analysis */}
      <div>
        <SectionHeading n={3} title="Complete Threat Analysis" />
        <ThreatCard analysis={report.threat_analysis} />
      </div>

      {/* 4. Item build */}
      <div>
        <SectionHeading n={4} title="Dynamic Item Builder" />
        <ItemBuildCard build={report.item_build} />
      </div>

      {/* 5 + 6. Skill build & talents */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="5 · Skill Build (1-30)" icon={<Layers className="h-4 w-4 text-magic" />}>
          <div className="flex flex-wrap gap-1">
            {sb.levels.map((l) => (
              <span
                key={l.level}
                title={`Lv ${l.level} · ${l.choice} — ${l.reason}`}
                className={cn(
                  'flex h-8 w-8 flex-col items-center justify-center rounded-md border text-[10px] font-bold leading-none',
                  l.kind === 'ultimate' && 'border-gold/60 bg-gold/15 text-gold',
                  l.kind === 'talent' && 'border-magic/60 bg-magic/15 text-magic',
                  l.kind === 'stats' && 'border-base-600 bg-base-800 text-slate-400',
                  l.kind === 'basic' && 'border-base-600 bg-base-850 text-slate-200',
                )}
              >
                <span className="text-[8px] opacity-60">{l.level}</span>
                {l.kind === 'basic' ? l.choice.split(' ').map((w) => w[0]).join('').slice(0, 3) : l.kind === 'ultimate' ? 'ULT' : l.kind === 'talent' ? 'TAL' : 'STAT'}
              </span>
            ))}
          </div>
          <div className="mt-3 flex flex-col gap-1 text-xs text-slate-400">
            <p>
              <span className="font-semibold text-radiant">{sb.primary}</span> maxed first ·{' '}
              <span className="font-semibold text-slate-300">{sb.secondary}</span> second
              {sb.ultimate && (
                <>
                  {' '}
                  · <span className="font-semibold text-gold">{sb.ultimate}</span> at 6/12/18
                </>
              )}
            </p>
          </div>
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

        <Card title="6 · Talent Tree" icon={<Sparkles className="h-4 w-4 text-magic" />}>
          {talents.length === 0 ? (
            <p className="text-sm text-slate-500">No talent data for this hero.</p>
          ) : (
            <ul className="flex flex-col gap-2.5">
              {talents.map((t) => (
                <li key={t.hero_level} className="rounded-lg border border-base-700 bg-base-850/60 p-2.5">
                  <p className="label mb-1 text-magic">Level {t.hero_level}</p>
                  <p className="text-sm font-semibold text-white">{t.recommended}</p>
                  <p className="mt-0.5 text-[11px] text-slate-400">
                    Alternative: {t.options.filter((o) => o !== t.recommended).join(' / ') || '—'}
                  </p>
                  <p className="mt-1 text-[11px] italic text-slate-500">{t.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* 7. Match plan */}
      <Card title="7 · Match Plan" icon={<Clock className="h-4 w-4 text-gold" />}>
        <div className="flex flex-col gap-2.5">
          {report.match_plan.map((p) => (
            <div key={p.window} className="rounded-lg border border-base-700 bg-base-850/60 p-3">
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-gold/15 px-2 py-0.5 text-xs font-bold text-gold">{p.window} min</span>
                <span className="text-sm font-bold text-white">{p.phase}</span>
              </div>
              <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Objectives" value={p.objectives} />
                <Field label="Farm focus" value={p.farm_focus} />
                <Field label="Fight focus" value={p.fight_focus} />
                <Field label="Map movement" value={p.map_movement} />
                <Field label="Tower priority" value={p.tower_priority} />
                <Field label="Roshan priority" value={p.roshan_priority} />
                <Field label="Danger zones" value={p.danger_zones} tone="danger" />
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* 8 + 9 */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <SectionHeading n={8} title="Win Conditions" />
          <WinConditionsCard conditions={report.win_conditions} />
        </div>
        <div>
          <SectionHeading n={9} title="Target Priority" />
          <TargetPriorityCard targets={report.target_priority} />
        </div>
      </div>

      {/* 10 */}
      <div>
        <SectionHeading n={10} title="Power Spike Engine" />
        <PowerSpikeCard spikes={report.power_spikes} />
      </div>

      {/* 11 */}
      <div>
        <SectionHeading n={11} title="One-Sentence Win Plan" />
        <OneSentencePlan sentence={report.one_sentence_win_plan} label="Your final take-away" />
      </div>

      <p className="pb-2 text-center text-[11px] text-slate-600">
        Patch {report.patch ?? '—'} · computed in {report.generated_in_ms} ms · built on real OpenDota match
        statistics, not static guides.
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
