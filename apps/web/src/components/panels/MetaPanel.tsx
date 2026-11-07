'use client';

import { TrendingDown, TrendingUp, Flame } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Meta } from '@/lib/types';
import { groupThousands } from '@/lib/format';
import { Card } from '@/components/Card';

export function MetaPanel({ meta }: { meta: Meta | null }) {
  const t = useTranslations('metaPanel');
  if (!meta) {
    return (
      <Card>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card title={t('title')} icon={<Flame className="h-4 w-4 text-gold" />} action={<span className="chip">Patch {meta.patch ?? '—'}</span>}>
        <p className="text-sm text-slate-400">{t('description', { source: meta.source })}</p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <MetaList title={t('trending')} rows={meta.trending.map((row) => ({ name: row.hero, value: groupThousands(row.picks), sub: t('picks') }))} tone="neutral" icon={<Flame className="h-4 w-4 text-gold" />} />
        <MetaList title={t('winners')} rows={meta.patch_winners.map((row) => ({ name: row.hero, value: `${(row.cm_winrate * 100).toFixed(1)}%`, sub: t('cmWinrate') }))} tone="radiant" icon={<TrendingUp className="h-4 w-4 text-radiant" />} />
        <MetaList title={t('losers')} rows={meta.patch_losers.map((row) => ({ name: row.hero, value: `${(row.cm_winrate * 100).toFixed(1)}%`, sub: t('cmWinrate') }))} tone="dire" icon={<TrendingDown className="h-4 w-4 text-dire" />} />
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
