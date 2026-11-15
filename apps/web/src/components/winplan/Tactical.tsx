'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { cdn, cn } from '@/lib/format';
import type { ItemBuild, ItemPick, PowerSpike, ThreatAnalysis } from '@/lib/types';
import type { WinPlanView } from '@/lib/winplan';

/** Compact item row whose reasoning is reachable on hover (desktop) and tap (mobile). */
function ItemRow({ item, tone = 'default' }: { item: ItemPick; tone?: 'default' | 'danger' | 'gold' }) {
  const [open, setOpen] = useState(false);
  const src = item.img ? cdn(item.img) : '';
  return (
    <div
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
      className={cn(
        'group relative flex cursor-pointer items-center gap-2.5 rounded-lg border px-2.5 py-2 transition focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
        tone === 'danger'
          ? 'border-dire/45 bg-dire/10'
          : tone === 'gold'
            ? 'border-gold/45 bg-gold/10'
            : 'border-base-700 bg-base-900/60 hover:border-base-600',
      )}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" width={26} height={26} className="h-[26px] w-[26px] shrink-0 rounded" loading="lazy" />
      ) : (
        <span className="h-[26px] w-[26px] shrink-0 rounded bg-base-700" />
      )}
      <span className="min-w-0 flex-1 truncate text-xs font-medium text-ink-soft">{item.name}</span>
      {typeof item.cost === 'number' && item.cost > 0 && (
        <span className="tabular shrink-0 text-[10px] text-gold">{item.cost}</span>
      )}
      <span
        className={cn(
          'pointer-events-none absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-base-600 bg-base-950 p-2.5 text-[11px] leading-relaxed text-ink-muted shadow-xl group-hover:block',
          open ? 'block' : 'hidden',
        )}
      >
        {item.reason}
      </span>
    </div>
  );
}

const PHASES: { key: keyof ItemBuild; label: string; hint: string }[] = [
  { key: 'starting', label: 'starting', hint: 'hintStarting' },
  { key: 'lane', label: 'lane', hint: 'hintLane' },
  { key: 'early', label: 'early', hint: 'hintEarly' },
  { key: 'mid', label: 'mid', hint: 'hintMid' },
  { key: 'late', label: 'late', hint: 'hintLate' },
  { key: 'luxury', label: 'luxury', hint: 'hintLuxury' },
  { key: 'situational', label: 'situational', hint: 'hintSituational' },
  { key: 'emergency', label: 'emergency', hint: 'hintEmergency' },
];

/** Dynamic item build — phase progression with reasons, plus items to avoid. */
export function WinPlanItemBuild({ build }: { build: ItemBuild }) {
  const t = useTranslations('winplan.items');
  const counters = build.key_counters ?? [];
  const phases = PHASES.filter((p) => (build[p.key] as ItemPick[]).length > 0);

  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <p className="kicker">{t('title')}</p>
        <span className="chip border-base-600/60 text-ink-faint">{t('generated')}</span>
      </div>

      {counters.length > 0 && (
        <div className="mb-4 rounded-lg border border-gold/40 bg-gold/5 p-3">
          <p className="label mb-2 text-gold">{t('keyCounters')}</p>
          <div className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
            {counters.map((i) => (
              <ItemRow key={i.key} item={i} tone="gold" />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-x-5 gap-y-4 sm:grid-cols-2 xl:grid-cols-3">
        {phases.map((p) => (
          <div key={p.key}>
            <p className="label mb-1.5">
              {t(p.label)} <span className="font-normal normal-case tracking-normal text-ink-faint">· {t(p.hint)}</span>
            </p>
            <div className="flex flex-col gap-1.5">
              {(build[p.key] as ItemPick[]).map((i) => (
                <ItemRow key={`${p.key}-${i.key}`} item={i} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {build.avoid.length > 0 && (
        <div className="mt-4 rounded-lg border border-dire/40 bg-dire/5 p-3">
          <p className="label mb-2 text-dire">{t('avoid')}</p>
          <div className="grid gap-1.5 sm:grid-cols-2 xl:grid-cols-3">
            {build.avoid.map((i) => (
              <ItemRow key={`avoid-${i.key}`} item={i} tone="danger" />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

/** Threat analysis — dimension scores with danger colouring. */
export function WinPlanThreats({ analysis }: { analysis: ThreatAnalysis }) {
  const t = useTranslations('winplan');
  const rows = Object.entries(analysis.scores).sort((a, b) => b[1] - a[1]);
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('threats')}</p>
      <div className="grid gap-x-6 gap-y-2.5 sm:grid-cols-2 xl:grid-cols-3">
        {rows.map(([key, value]) => {
          const danger = analysis.danger[key];
          const bar = danger === 'high' ? 'bg-dire' : danger === 'medium' ? 'bg-gold' : 'bg-radiant';
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="w-28 shrink-0 truncate text-xs text-ink-muted">{analysis.labels[key] ?? key}</span>
              <span className="bar flex-1">
                <span className={cn('block h-full rounded-full', bar)} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
              </span>
              <span className="tabular w-9 shrink-0 text-right text-xs font-semibold text-ink-soft">{value.toFixed(0)}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/** Power spikes — your windows vs the enemy's. */
export function WinPlanPowerSpikes({ spikes }: { spikes: { player: PowerSpike[]; enemies: PowerSpike[] } }) {
  const t = useTranslations('winplan');
  if (spikes.player.length === 0 && spikes.enemies.length === 0) return null;
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('powerSpikes')}</p>
      <div className="grid gap-4 xl:grid-cols-2">
        <div>
          <p className="label mb-2 text-radiant">{t('yourSpikes')}</p>
          <ol className="flex flex-col gap-2">
            {spikes.player.map((s, i) => (
              <li key={i} className="rounded-lg border border-radiant/25 bg-radiant/5 p-2.5">
                <p className="text-xs font-bold text-radiant">
                  {s.when} <span className="font-normal text-ink-faint">· {s.type}</span>
                </p>
                {s.detail && <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">{s.detail}</p>}
              </li>
            ))}
          </ol>
        </div>
        <div>
          <p className="label mb-2 text-dire">{t('enemySpikes')}</p>
          <ol className="flex flex-col gap-2">
            {spikes.enemies.map((s, i) => (
              <li key={i} className="rounded-lg border border-base-700 bg-base-900/60 p-2.5">
                <p className="text-xs font-bold text-ink-soft">
                  {s.name} <span className="font-normal text-ink-faint">· {s.peak_minutes ?? 0}′</span>
                </p>
                {s.danger && <p className="mt-0.5 text-[11px] leading-relaxed text-ink-muted">{s.danger}</p>}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/** Danger heroes — the enemies most able to break the plan. */
export function WinPlanDangerHeroes({ heroes }: { heroes: WinPlanView['dangerHeroes'] }) {
  const t = useTranslations('winplan');
  if (heroes.length === 0) return null;
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('dangerHeroes')}</p>
      <div className="grid gap-2 sm:grid-cols-3">
        {heroes.map((h) => (
          <div key={h.heroId} className="rounded-lg border border-base-700 bg-base-900/60 p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="truncate text-sm font-semibold text-ink">{h.name}</p>
              <span className="tabular text-xs font-bold text-dire">{h.score.toFixed(0)}</span>
            </div>
            {h.reason && <p className="mt-1 line-clamp-3 text-[11px] leading-relaxed text-ink-muted">{h.reason}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}

/** Tactical phases — early / mid / late. */
export function WinPlanPhases({ phases }: { phases: WinPlanView['phases'] }) {
  const t = useTranslations('winplan');
  if (phases.length === 0) return null;
  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <p className="kicker mb-3">{t('phases')}</p>
      <div className="grid gap-3 lg:grid-cols-2 xl:grid-cols-3">
        {phases.map((p) => (
          <div key={p.window} className="well p-3">
            <p className="tabular text-xs font-bold text-accent">{p.window}</p>
            <p className="mb-2 text-[11px] uppercase tracking-wide text-ink-faint">{p.phase}</p>
            <dl className="flex flex-col gap-1.5 text-[11px] leading-relaxed">
              {p.objectives.length > 0 && (
                <div>
                  <dt className="font-semibold text-ink-muted">{t('phases.objectives')}</dt>
                  <dd className="text-ink-soft">{p.objectives.join(' · ')}</dd>
                </div>
              )}
              {p.farmFocus && (
                <div>
                  <dt className="font-semibold text-ink-muted">{t('phases.farm')}</dt>
                  <dd className="text-ink-soft">{p.farmFocus}</dd>
                </div>
              )}
              {p.fightFocus && (
                <div>
                  <dt className="font-semibold text-ink-muted">{t('phases.fight')}</dt>
                  <dd className="text-ink-soft">{p.fightFocus}</dd>
                </div>
              )}
              {p.mapMovement && (
                <div>
                  <dt className="font-semibold text-ink-muted">{t('phases.map')}</dt>
                  <dd className="text-ink-soft">{p.mapMovement}</dd>
                </div>
              )}
            </dl>
          </div>
        ))}
      </div>
    </section>
  );
}
