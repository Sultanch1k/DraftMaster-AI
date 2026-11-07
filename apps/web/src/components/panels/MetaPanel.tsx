'use client';

import { TrendingDown, TrendingUp, Flame } from 'lucide-react';
import type { Meta } from '@/lib/types';
import { Card } from '@/components/Card';

export function MetaPanel({ meta }: { meta: Meta | null }) {
  if (!meta) {
    return (
      <Card>
        <p className="text-sm text-slate-400">Loading live meta intelligence from OpenDota…</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card title="Meta Intelligence" icon={<Flame className="h-4 w-4 text-gold" />} action={<span className="chip">Patch {meta.patch ?? '—'}</span>}>
        <p className="text-sm text-slate-400">
          Computed from {meta.source}. Patch winners and losers are ranked by Captain&apos;s Mode win rate,
          trending heroes by public pick rate.
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <MetaList title="Trending heroes" rows={meta.trending.map((t) => ({ name: t.hero, value: t.picks.toLocaleString(), sub: 'picks' }))} tone="neutral" icon={<Flame className="h-4 w-4 text-gold" />} />
        <MetaList title="Patch winners" rows={meta.patch_winners.map((t) => ({ name: t.hero, value: `${(t.cm_winrate * 100).toFixed(1)}%`, sub: 'CM win rate' }))} tone="radiant" icon={<TrendingUp className="h-4 w-4 text-radiant" />} />
        <MetaList title="Patch losers" rows={meta.patch_losers.map((t) => ({ name: t.hero, value: `${(t.cm_winrate * 100).toFixed(1)}%`, sub: 'CM win rate' }))} tone="dire" icon={<TrendingDown className="h-4 w-4 text-dire" />} />
      </div>
    </div>
  );
}

function MetaList({
  title,
  rows,
  tone,
  icon,
}: {
  title: string;
  rows: { name: string; value: string; sub: string }[];
  tone: 'radiant' | 'dire' | 'neutral';
  icon: React.ReactNode;
}) {
  const valueCls = tone === 'radiant' ? 'text-radiant' : tone === 'dire' ? 'text-dire' : 'text-gold';
  return (
    <Card title={title} icon={icon}>
      <ol className="flex flex-col gap-1.5">
        {rows.map((r, i) => (
          <li key={r.name} className="flex items-center gap-2 rounded-md border border-base-700 bg-base-850/60 px-2.5 py-1.5">
            <span className="w-5 shrink-0 text-[11px] tabular-nums text-slate-500">{i + 1}</span>
            <span className="flex-1 truncate text-sm text-slate-200">{r.name}</span>
            <span className={`shrink-0 text-xs font-bold tabular-nums ${valueCls}`}>{r.value}</span>
          </li>
        ))}
      </ol>
    </Card>
  );
}
