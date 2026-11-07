'use client';

import { cn, RANKS, ROLES } from '@/lib/format';

type Props = {
  role: string;
  onRole: (r: string) => void;
  rank: number;
  onRank: (r: number) => void;
  compact?: boolean;
};

export function DraftControls({ role, onRole, rank, onRank, compact }: Props) {
  return (
    <div className={cn('grid gap-3', compact ? 'grid-cols-2' : 'sm:grid-cols-2')}>
      <div>
        <label className="label mb-1 block">Your role</label>
        <div className="flex flex-wrap gap-1.5">
          {ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onRole(r.value)}
              className={cn('chip', role === r.value && 'border-radiant/60 bg-radiant/10 text-radiant')}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
      <div>
        <label className="label mb-1 block">Your rank</label>
        <div className="flex flex-wrap gap-1.5">
          {RANKS.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onRank(r.value)}
              className={cn('chip', rank === r.value && 'border-radiant/60 bg-radiant/10 text-radiant')}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
