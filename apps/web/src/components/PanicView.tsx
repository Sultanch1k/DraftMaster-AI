'use client';

import { useState } from 'react';
import { Ban, Flame, Target, Zap } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ItemPick, PanicResult } from '@/lib/types';
import { cn } from '@/lib/format';
import { HeroPortrait } from './HeroPortrait';
import { WinProbabilityBar } from './WinProbability';
import { OneSentencePlan } from './ReportCards';
import { StatRow } from './Bar';

/**
 * "I'M LAST PICK" result — engineered to be scannable in one screen during a
 * real draft. Everything above the fold is the decision; the reasoning lives in
 * hover/tap detail and in the full report.
 */
export function PanicView({ result, onFullReport }: { result: PanicResult; onFullReport?: () => void }) {
  const t = useTranslations('panic');
  const b = result.full_build;
  // "Full build" = the ordered progression, deduped, so a one-screen glance still
  // shows the real sequence (lane -> early -> mid -> late) rather than a subset.
  const coreItems = dedupeItems([...b.lane, ...b.early, ...b.mid, ...b.late]).slice(0, 8);
  const counters = b.key_counters ?? [];

  return (
    <div className="flex flex-col gap-3">
      <OneSentencePlan sentence={result.one_sentence_win_plan} />

      <div className="grid gap-3 xl:grid-cols-[1.15fr_1fr]">
        {/* Decision column */}
        <div className="card card-pad flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <HeroPortrait icon={result.best_hero.icon} name={result.best_hero.localized_name} size={72} priority />
            <div className="min-w-0 flex-1">
              <p className="label text-radiant">{t('bestPick')}</p>
              <h2 className="truncate text-2xl font-black leading-tight text-white">
                {result.best_hero.localized_name}
              </h2>
              <p className="truncate text-xs text-slate-400">{result.best_hero.roles.join(' · ')}</p>
            </div>
            <div className="text-right">
              <p className="label">{t('pickScore')}</p>
              <p className="text-2xl font-black tabular-nums text-radiant">{result.best_hero.final_score.toFixed(1)}</p>
            </div>
          </div>

          {result.why_this_hero[0] && (
            <p className="rounded-lg border border-base-700 bg-base-900/60 p-2.5 text-sm leading-relaxed text-slate-200">
              {result.why_this_hero[0]}
            </p>
          )}

          <WinProbabilityBar wp={result.win_probability} compact />

          {result.backups.length > 0 && (
            <div>
              <p className="label mb-1.5">{t('backups')}</p>
              <div className="flex flex-wrap gap-2">
                {result.backups.slice(0, 4).map((p, i) => (
                  <div key={p.hero_id} className="flex items-center gap-2 rounded-lg border border-base-700 bg-base-850/70 px-2 py-1">
                    <span className="text-[10px] font-bold text-slate-500">#{i + 2}</span>
                    <HeroPortrait icon={p.icon} name={p.localized_name} size={26} />
                    <span className="text-xs text-slate-300">{p.localized_name}</span>
                    <span className="text-[10px] tabular-nums text-slate-500">{p.final_score.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Intel column */}
        <div className="card card-pad flex flex-col gap-3">
          <div>
            <p className="label mb-1.5 flex items-center gap-1.5 text-gold">
              <Zap className="h-3.5 w-3.5" /> {t('fullBuild')}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {coreItems.map((i) => (
                <PanicItem key={i.key} item={i} />
              ))}
            </div>
          </div>

          {counters.length > 0 && (
            <div>
              <p className="label mb-1.5 text-gold">{t('keyCounters')}</p>
              <div className="flex flex-wrap gap-1.5">
                {counters.map((i) => (
                  <span key={i.key} className="rounded-md border border-gold/50 bg-gold/10 px-2 py-1 text-[11px] font-semibold text-gold">
                    {i.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="label mb-1.5 flex items-center gap-1.5 text-dire">
                <Target className="h-3.5 w-3.5" /> {t('killOrder')}
              </p>
              <ol className="flex flex-col gap-1">
                {result.kill_priority.map((row) => (
                  <li key={row.hero_id} className="flex items-center gap-1.5 text-xs text-slate-300">
                    <span className="flex h-4 w-4 items-center justify-center rounded-full bg-dire/20 text-[9px] font-bold text-dire">
                      {row.rank}
                    </span>
                    <span className="truncate">{row.name}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div>
              <p className="label mb-1.5 flex items-center gap-1.5 text-gold">
                <Flame className="h-3.5 w-3.5" /> {t('dangerHeroes')}
              </p>
              <ol className="flex flex-col gap-1">
                {result.danger_heroes.slice(0, 4).map((row) => (
                  <li key={row.hero_id} className="flex items-center gap-1.5 text-xs text-slate-300">
                    <span className="truncate">{row.name}</span>
                    <span className="ml-auto text-[10px] tabular-nums text-dire">{row.priority_score.toFixed(0)}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>

          {result.items_to_avoid.length > 0 && (
            <div>
              <p className="label mb-1.5 flex items-center gap-1.5 text-dire">
                <Ban className="h-3.5 w-3.5" /> {t('doNotBuild')}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {result.items_to_avoid.slice(0, 6).map((i) => (
                  <span key={i.key} className="rounded-md border border-dire/50 bg-dire/10 px-2 py-1 text-[11px] text-dire">
                    {i.name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {(
          [
            [t('primary'), result.win_conditions.primary, 'border-radiant/40 text-radiant'],
            [t('secondary'), result.win_conditions.secondary, 'border-gold/40 text-gold'],
            [t('emergency'), result.win_conditions.emergency, 'border-dire/40 text-dire'],
          ] as const
        ).map(([label, text, cls]) => (
          <div key={label} className={cn('card card-pad border', cls)}>
            <p className="label mb-1">{t('winCondition', { tier: label })}</p>
            <p className="text-xs leading-relaxed text-slate-200">{text}</p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span>
          {t('generatedIn', { ms: result.generated_in_ms })}
          {result.usage && (
            <>
              {' · '}
              {result.usage.plan === 'premium' ? t('premiumPlan') : t('freePlan')}
              {result.usage.remaining != null && ` · ${t('analysesLeft', { count: result.usage.remaining })}`}
            </>
          )}
        </span>
        {onFullReport && (
          <button type="button" onClick={onFullReport} className="btn-ghost !py-1.5 text-xs">
            {t('openFull')}
          </button>
        )}
      </div>
    </div>
  );
}

/** Build chip whose reasoning is reachable on hover (desktop) and tap (mobile). */
function PanicItem({ item }: { item: ItemPick }) {
  const [open, setOpen] = useState(false);
  return (
    <span
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen((v) => !v)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setOpen((v) => !v);
        }
      }}
      onBlur={() => setOpen(false)}
      className="group relative cursor-pointer rounded-md border border-base-700 bg-base-850/70 px-2 py-1 text-[11px] text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-radiant/60"
    >
      {item.name}
      <span
        className={cn(
          'pointer-events-none absolute left-0 top-full z-20 mt-1 w-56 rounded-lg border border-base-600 bg-base-900 p-2 text-[11px] text-slate-300 shadow-xl group-hover:block',
          open ? 'block' : 'hidden',
        )}
      >
        {item.reason}
      </span>
    </span>
  );
}

/** Keep the first occurrence of each item so the progression reads without repeats. */
function dedupeItems(items: ItemPick[]): ItemPick[] {
  const seen = new Set<string>();
  const out: ItemPick[] = [];
  for (const item of items) {
    if (seen.has(item.key)) continue;
    seen.add(item.key);
    out.push(item);
  }
  return out;
}
