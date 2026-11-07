'use client';

import { AlertTriangle, Ban, ShieldAlert, Sparkles, Swords, Target } from 'lucide-react';
import type { ItemBuild, ItemPick, PickCandidate, PowerSpike, TargetRow } from '@/lib/types';
import { cn, scoreColor } from '@/lib/format';
import { HeroPortrait } from './HeroPortrait';
import { Card } from './Card';
import { StatRow } from './Bar';

export function BestHeroCard({ pick, rank = 1 }: { pick: PickCandidate; rank?: number }) {
  return (
    <div
      className={cn(
        'flex gap-3 rounded-xl border p-3',
        rank === 1 ? 'border-radiant/50 bg-radiant/5 shadow-glow' : 'border-base-700 bg-base-850/60',
      )}
    >
      <HeroPortrait icon={pick.icon} name={pick.localized_name} size={rank === 1 ? 64 : 48} priority={rank === 1} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-black', rank === 1 ? 'text-radiant' : 'text-slate-400')}>#{rank}</span>
          <h3 className="truncate text-base font-bold text-white">{pick.localized_name}</h3>
          <span className={cn('ml-auto text-lg font-black tabular-nums', scoreColor(pick.final_score))}>
            {pick.final_score.toFixed(1)}
          </span>
        </div>
        <p className="mb-2 text-[11px] text-slate-400">{pick.roles.join(' · ')}</p>
        {pick.reasons[0] && <p className="text-xs leading-relaxed text-slate-300">{pick.reasons[0]}</p>}
        {rank === 1 && (
          <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1">
            <StatRow label="Counter" value={pick.scores.counter} />
            <StatRow label="Lane" value={pick.scores.lane} />
            <StatRow label="Meta" value={pick.scores.meta} />
            <StatRow label="Comfort" value={pick.scores.comfort} />
          </div>
        )}
      </div>
    </div>
  );
}

const PHASES: { key: keyof ItemBuild; label: string; hint: string }[] = [
  { key: 'starting', label: 'Starting', hint: 'Leaving base' },
  { key: 'lane', label: 'Lane', hint: 'Laning stage' },
  { key: 'early', label: 'Early Game', hint: 'First items' },
  { key: 'mid', label: 'Mid Game', hint: 'Core timing' },
  { key: 'late', label: 'Late Game', hint: 'Scaling' },
  { key: 'luxury', label: 'Luxury', hint: '6-slot' },
  { key: 'situational', label: 'Situational', hint: 'If needed' },
  { key: 'emergency', label: 'Emergency', hint: 'Losing hard' },
];

function ItemChip({ item, tone = 'default' }: { item: ItemPick; tone?: 'default' | 'danger' | 'gold' }) {
  return (
    <div
      className={cn(
        'group relative flex items-center gap-2 rounded-lg border px-2 py-1.5',
        tone === 'danger'
          ? 'border-dire/50 bg-dire/10'
          : tone === 'gold'
            ? 'border-gold/50 bg-gold/10'
            : 'border-base-700 bg-base-850/70',
      )}
    >
      {item.img ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={`https://cdn.cloudflare.steamstatic.com${item.img.split('?')[0]}`} alt="" width={24} height={24} className="h-6 w-6 rounded" loading="lazy" />
      ) : (
        <span className="h-6 w-6 rounded bg-base-700" />
      )}
      <span className="min-w-0 flex-1 truncate text-xs font-medium text-slate-200">{item.name}</span>
      {typeof item.cost === 'number' && item.cost > 0 && (
        <span className="shrink-0 text-[10px] tabular-nums text-gold">{item.cost}</span>
      )}
      <span className="pointer-events-none absolute left-0 top-full z-20 mt-1 hidden w-64 rounded-lg border border-base-600 bg-base-900 p-2 text-[11px] leading-relaxed text-slate-300 shadow-xl group-hover:block">
        {item.reason}
      </span>
    </div>
  );
}

export function ItemBuildCard({ build }: { build: ItemBuild }) {
  const counters = build.key_counters ?? [];
  return (
    <Card
      title="Dynamic Item Build"
      icon={<Sparkles className="h-4 w-4 text-gold" />}
      action={<span className="chip">generated from your enemy draft</span>}
    >
      {counters.length > 0 && (
        <div className="mb-4 rounded-lg border border-gold/40 bg-gold/5 p-3">
          <p className="label mb-2 text-gold">Key counter items — buy these or lose</p>
          <div className="flex flex-wrap gap-2">
            {counters.map((i) => (
              <ItemChip key={i.key} item={i} tone="gold" />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {PHASES.filter((p) => (build[p.key] as ItemPick[]).length > 0).map((p) => (
          <div key={p.key}>
            <p className="label mb-1.5">
              {p.label} <span className="font-normal normal-case text-slate-500">· {p.hint}</span>
            </p>
            <div className="flex flex-col gap-1.5">
              {(build[p.key] as ItemPick[]).map((i) => (
                <ItemChip key={`${p.key}-${i.key}`} item={i} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {build.avoid.length > 0 && (
        <div className="mt-4 rounded-lg border border-dire/40 bg-dire/5 p-3">
          <p className="label mb-2 flex items-center gap-1.5 text-dire">
            <Ban className="h-3.5 w-3.5" /> Items to avoid
          </p>
          <div className="flex flex-wrap gap-2">
            {build.avoid.map((i) => (
              <ItemChip key={`avoid-${i.key}`} item={i} tone="danger" />
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export function ThreatCard({ analysis }: { analysis: { scores: Record<string, number>; labels: Record<string, string>; danger: Record<string, string> } }) {
  const rows = Object.entries(analysis.scores).sort((a, b) => b[1] - a[1]);
  return (
    <Card title="Threat Analysis" icon={<ShieldAlert className="h-4 w-4 text-dire" />}>
      <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {rows.map(([key, value]) => (
          <StatRow key={key} label={analysis.labels[key] ?? key} value={value} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
        <span className="chip border-radiant/40 text-radiant">low 0-39</span>
        <span className="chip border-gold/40 text-gold">medium 40-64</span>
        <span className="chip border-dire/40 text-dire">high 65+</span>
      </div>
    </Card>
  );
}

export function TargetPriorityCard({ targets }: { targets: TargetRow[] }) {
  return (
    <Card title="Kill Priority" icon={<Target className="h-4 w-4 text-dire" />}>
      <ol className="flex flex-col gap-2">
        {targets.map((t) => (
          <li key={t.hero_id} className="flex items-center gap-3 rounded-lg border border-base-700 bg-base-850/60 p-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-dire/20 text-sm font-black text-dire">
              {t.rank}
            </span>
            <HeroPortrait icon={null} name={t.name} size={32} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{t.name}</p>
              <p className="truncate text-[11px] text-slate-400">{t.reason}</p>
            </div>
            <span className="shrink-0 text-sm font-bold tabular-nums text-dire">{t.priority_score.toFixed(0)}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function PowerSpikeCard({ spikes }: { spikes: { player: PowerSpike[]; enemies: PowerSpike[] } }) {
  return (
    <Card title="Power Spikes" icon={<Swords className="h-4 w-4 text-gold" />}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <p className="label mb-2 text-radiant">Your spikes</p>
          <ul className="flex flex-col gap-2">
            {spikes.player.map((s, i) => (
              <li key={i} className="rounded-lg border border-radiant/30 bg-radiant/5 p-2">
                <p className="text-xs font-bold text-radiant">
                  {s.when} <span className="font-normal text-slate-400">· {s.type}</span>
                </p>
                <p className="text-[11px] text-slate-300">{s.detail}</p>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <p className="label mb-2 text-dire">Enemy spikes</p>
          <ul className="flex flex-col gap-2">
            {spikes.enemies.map((s, i) => (
              <li key={i} className="rounded-lg border border-base-700 bg-base-850/60 p-2">
                <p className="text-xs font-bold text-slate-200">
                  {s.name} <span className="font-normal text-slate-500">· peak ~{s.peak_minutes}m</span>
                </p>
                <p className="text-[11px] text-slate-400">{s.danger}</p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

export function WinConditionsCard({ conditions }: { conditions: { primary: string; secondary: string; emergency: string } }) {
  const rows = [
    { label: 'Primary Win Condition', value: conditions.primary, tone: 'radiant' },
    { label: 'Secondary Win Condition', value: conditions.secondary, tone: 'gold' },
    { label: 'Emergency Win Condition', value: conditions.emergency, tone: 'dire' },
  ];
  return (
    <Card title="Win Conditions" icon={<Target className="h-4 w-4 text-radiant" />}>
      <div className="flex flex-col gap-2.5">
        {rows.map((r) => (
          <div
            key={r.label}
            className={cn(
              'rounded-lg border p-3',
              r.tone === 'radiant' && 'border-radiant/40 bg-radiant/5',
              r.tone === 'gold' && 'border-gold/40 bg-gold/5',
              r.tone === 'dire' && 'border-dire/40 bg-dire/5',
            )}
          >
            <p className={cn('label mb-1', r.tone === 'radiant' && 'text-radiant', r.tone === 'gold' && 'text-gold', r.tone === 'dire' && 'text-dire')}>
              {r.label}
            </p>
            <p className="text-sm leading-relaxed text-slate-200">{r.value}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

export function OneSentencePlan({ sentence, label = 'One-Sentence Win Plan' }: { sentence: string; label?: string }) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-radiant/50 bg-gradient-to-br from-radiant/10 to-transparent p-4">
      <p className="label mb-1.5 flex items-center gap-1.5 text-radiant">
        <AlertTriangle className="h-3.5 w-3.5" /> {label}
      </p>
      <p className="text-base font-semibold leading-relaxed text-white">{sentence}</p>
    </div>
  );
}
