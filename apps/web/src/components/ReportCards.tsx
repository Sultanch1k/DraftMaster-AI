'use client';

import { useState } from 'react';
import { AlertTriangle, Ban, Loader2, ShieldAlert, Sparkles, Swords, Target } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { ItemBuild, ItemPick, PickCandidate, PowerSpike, TargetRow } from '@/lib/types';
import { cn, scoreColor } from '@/lib/format';
import { HeroPortrait } from './HeroPortrait';
import { Card } from './Card';
import { StatRow } from './Bar';

export function BestHeroCard({
  pick,
  rank = 1,
  selected = false,
  loading = false,
  onSelect,
}: {
  pick: PickCandidate;
  rank?: number;
  selected?: boolean;
  loading?: boolean;
  onSelect?: () => void;
}) {
  const t = useTranslations('picks');
  const interactive = Boolean(onSelect);

  return (
    <div
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      aria-pressed={interactive ? selected : undefined}
      aria-label={interactive ? t('viewReport', { hero: pick.localized_name }) : undefined}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (!interactive) return;
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect?.();
        }
      }}
      className={cn(
        'relative flex gap-3 rounded-xl border p-3 transition',
        interactive && 'cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-radiant/60',
        selected
          ? 'border-radiant bg-radiant/10 shadow-glow ring-1 ring-radiant/40'
          : rank === 1
            ? 'border-radiant/40 bg-radiant/5 hover:border-radiant/70'
            : 'border-base-700 bg-base-850/60 hover:border-base-600 hover:bg-base-800',
      )}
    >
      {selected && (
        <span className="absolute -top-2 left-3 rounded-full bg-radiant px-2 py-0.5 text-[10px] font-bold text-base-950">
          {t('selected')}
        </span>
      )}
      <HeroPortrait icon={pick.icon} name={pick.localized_name} size={rank === 1 ? 64 : 48} priority={rank === 1} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={cn('text-xs font-black', rank === 1 ? 'text-radiant' : 'text-slate-400')}>#{rank}</span>
          <h3 className="truncate text-base font-bold text-white">{pick.localized_name}</h3>
          {loading ? (
            <Loader2 className="ml-auto h-4 w-4 animate-spin text-radiant" />
          ) : (
            <span className={cn('ml-auto text-lg font-black tabular-nums', scoreColor(pick.final_score))}>
              {pick.final_score.toFixed(1)}
            </span>
          )}
        </div>
        <p className="mb-2 text-[11px] text-slate-400">{pick.roles.join(' · ')}</p>
        {pick.reasons[0] && <p className="text-xs leading-relaxed text-slate-300">{pick.reasons[0]}</p>}
        <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
          <StatRow label={t('counter')} value={pick.scores.counter} />
          <StatRow label={t('lane')} value={pick.scores.lane} />
          <StatRow label={t('meta')} value={pick.scores.meta} />
          <StatRow label={t('comfort')} value={pick.scores.comfort} />
          <StatRow label={t('synergy')} value={pick.scores.synergy} />
          <StatRow label={t('difficulty')} value={pick.scores.difficulty} />
        </div>
        {selected && <p className="mt-2 text-[10px] font-semibold uppercase tracking-wide text-radiant">{t('selectedHint', { hero: pick.localized_name })}</p>}
      </div>
    </div>
  );
}

const PHASE_KEYS: { key: keyof ItemBuild; label: string; hint: string }[] = [
  { key: 'starting', label: 'starting', hint: 'hintStarting' },
  { key: 'lane', label: 'lane', hint: 'hintLane' },
  { key: 'early', label: 'early', hint: 'hintEarly' },
  { key: 'mid', label: 'mid', hint: 'hintMid' },
  { key: 'late', label: 'late', hint: 'hintLate' },
  { key: 'luxury', label: 'luxury', hint: 'hintLuxury' },
  { key: 'situational', label: 'situational', hint: 'hintSituational' },
  { key: 'emergency', label: 'emergency', hint: 'hintEmergency' },
];

function ItemChip({ item, tone = 'default' }: { item: ItemPick; tone?: 'default' | 'danger' | 'gold' }) {
  const [open, setOpen] = useState(false);
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
        'group relative flex cursor-pointer items-center gap-2 rounded-lg border px-2 py-1.5 focus:outline-none focus-visible:ring-2 focus-visible:ring-radiant/60',
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
      {/* Reasoning is reachable by hover (desktop) and by tap/click (mobile + keyboard). */}
      <span
        className={cn(
          'pointer-events-none absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-base-600 bg-base-900 p-2 text-[11px] leading-relaxed text-slate-300 shadow-xl group-hover:block',
          open ? 'block' : 'hidden',
        )}
      >
        {item.reason}
      </span>
    </div>
  );
}

export function ItemBuildCard({ build }: { build: ItemBuild }) {
  const t = useTranslations('items');
  const counters = build.key_counters ?? [];
  return (
    <Card
      title={t('title')}
      icon={<Sparkles className="h-4 w-4 text-gold" />}
      action={<span className="chip">{t('generatedFromDraft')}</span>}
    >
      {counters.length > 0 && (
        <div className="mb-4 rounded-lg border border-gold/40 bg-gold/5 p-3">
          <p className="label mb-2 text-gold">{t('keyCounters')}</p>
          <div className="flex flex-wrap gap-2">
            {counters.map((i) => (
              <ItemChip key={i.key} item={i} tone="gold" />
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {PHASE_KEYS.filter((p) => (build[p.key] as ItemPick[]).length > 0).map((p) => (
          <div key={p.key}>
            <p className="label mb-1.5">
              {t(p.label)} <span className="font-normal normal-case text-slate-500">· {t(p.hint)}</span>
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
            <Ban className="h-3.5 w-3.5" /> {t('avoid')}
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
  const t = useTranslations('threats');
  const rows = Object.entries(analysis.scores).sort((a, b) => b[1] - a[1]);
  return (
    <Card title={t('title')} icon={<ShieldAlert className="h-4 w-4 text-dire" />}>
      <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2 xl:grid-cols-3">
        {rows.map(([key, value]) => (
          <StatRow key={key} label={analysis.labels[key] ?? key} value={value} />
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
        <span className="chip border-radiant/40 text-radiant">{t('low')}</span>
        <span className="chip border-gold/40 text-gold">{t('medium')}</span>
        <span className="chip border-dire/40 text-dire">{t('high')}</span>
      </div>
    </Card>
  );
}

export function TargetPriorityCard({ targets }: { targets: TargetRow[] }) {
  const t = useTranslations('targets');
  return (
    <Card title={t('title')} icon={<Target className="h-4 w-4 text-dire" />}>
      <ol className="flex flex-col gap-2">
        {targets.map((row) => (
          <li key={row.hero_id} className="flex items-center gap-3 rounded-lg border border-base-700 bg-base-850/60 p-2">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-dire/20 text-sm font-black text-dire">
              {row.rank}
            </span>
            <HeroPortrait icon={null} name={row.name} size={32} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-white">{row.name}</p>
              <p className="truncate text-[11px] text-slate-400">{row.reason}</p>
            </div>
            <span className="shrink-0 text-sm font-bold tabular-nums text-dire">{row.priority_score.toFixed(0)}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

export function PowerSpikeCard({ spikes }: { spikes: { player: PowerSpike[]; enemies: PowerSpike[] } }) {
  const t = useTranslations('spikes');
  return (
    <Card title={t('title')} icon={<Swords className="h-4 w-4 text-gold" />}>
      <div className="grid gap-4 xl:grid-cols-2">
        <div>
          <p className="label mb-2 text-radiant">{t('yours')}</p>
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
          <p className="label mb-2 text-dire">{t('enemies')}</p>
          <ul className="flex flex-col gap-2">
            {spikes.enemies.map((s, i) => (
              <li key={i} className="rounded-lg border border-base-700 bg-base-850/60 p-2">
                <p className="text-xs font-bold text-slate-200">
                  {s.name} <span className="font-normal text-slate-500">· {t('peak', { minutes: s.peak_minutes ?? 0 })}</span>
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
  const t = useTranslations('winConditions');
  const rows = [
    { label: t('primary'), value: conditions.primary, tone: 'radiant' },
    { label: t('secondary'), value: conditions.secondary, tone: 'gold' },
    { label: t('emergency'), value: conditions.emergency, tone: 'dire' },
  ];
  return (
    <Card title={t('title')} icon={<Target className="h-4 w-4 text-radiant" />}>
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

export function OneSentencePlan({ sentence, label }: { sentence: string; label?: string }) {
  const t = useTranslations('oneSentence');
  return (
    <div className="relative overflow-hidden rounded-xl border border-radiant/50 bg-gradient-to-br from-radiant/10 to-transparent p-4">
      <p className="label mb-1.5 flex items-center gap-1.5 text-radiant">
        <AlertTriangle className="h-3.5 w-3.5" /> {label ?? t('title')}
      </p>
      <p className="text-base font-semibold leading-relaxed text-white">{sentence}</p>
    </div>
  );
}
