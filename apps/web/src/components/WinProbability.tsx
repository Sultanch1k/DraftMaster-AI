'use client';

import { cn } from '@/lib/format';
import type { WinProbability } from '@/lib/types';

export function WinProbabilityBar({ wp, compact = false }: { wp: WinProbability; compact?: boolean }) {
  const you = wp.player_win_probability;
  const them = wp.enemy_win_probability;
  const edge = you >= them;

  return (
    <div className={cn('flex flex-col gap-2', compact && 'gap-1.5')}>
      <div className="flex items-end justify-between gap-3">
        <div>
          <p className="label">Draft Win Probability</p>
          <p className={cn('text-3xl font-black tabular-nums leading-none', edge ? 'text-radiant' : 'text-dire')}>
            {you.toFixed(1)}
            <span className="text-lg">%</span>
          </p>
        </div>
        <div className="text-right">
          <p className="label">Enemy</p>
          <p className="text-xl font-bold tabular-nums leading-none text-slate-300">{them.toFixed(1)}%</p>
        </div>
      </div>

      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-base-700">
        <div
          className={cn('h-full transition-all duration-700', edge ? 'bg-radiant' : 'bg-dire')}
          style={{ width: `${you}%` }}
        />
        <div className="h-full flex-1 bg-base-600" />
      </div>

      <div className="flex items-center justify-between gap-2 text-xs">
        <span className={cn('font-semibold', edge ? 'text-radiant' : 'text-dire')}>{wp.verdict}</span>
        <span className="chip capitalize">{wp.confidence} confidence</span>
      </div>
    </div>
  );
}

export function WinProbFactors({ wp }: { wp: WinProbability }) {
  return (
    <ul className="flex flex-col gap-2">
      {wp.factors.map((f) => {
        const positive = f.contribution_pp >= 0;
        return (
          <li key={f.name} className="flex items-start gap-3 text-sm">
            <span
              className={cn(
                'mt-0.5 w-14 shrink-0 rounded px-1.5 py-0.5 text-center text-xs font-bold tabular-nums',
                positive ? 'bg-radiant/15 text-radiant' : 'bg-dire/15 text-dire',
              )}
            >
              {positive ? '+' : ''}
              {f.contribution_pp.toFixed(1)}
            </span>
            <span className="flex-1">
              <span className="font-semibold text-slate-200">{f.name}</span>
              <span className="block text-xs text-slate-400">{f.detail}</span>
            </span>
          </li>
        );
      })}
      <li className="pt-1 text-[11px] text-slate-500">
        Contributions are percentage points from a 50% baseline, then compressed toward 50% by rank
        ({wp.rank_label}) — higher ranks convert draft edges into wins more reliably.
      </li>
    </ul>
  );
}
