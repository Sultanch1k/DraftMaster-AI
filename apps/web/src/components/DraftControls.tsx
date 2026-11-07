'use client';

import { useTranslations } from 'next-intl';
import { cn, RANKS, ROLES } from '@/lib/format';

type Props = {
  role: string;
  onRole: (r: string) => void;
  rank: number;
  onRank: (r: number) => void;
  compact?: boolean;
};

export function DraftControls({ role, onRole, rank, onRank, compact }: Props) {
  const t = useTranslations('draft');
  const tRoles = useTranslations('roles');
  const tRanks = useTranslations('ranks');
  return (
    <div className={cn('grid gap-3', compact ? 'grid-cols-2' : 'sm:grid-cols-2')}>
      <div>
        <label className="label mb-1 block">{t('yourRole')}</label>
        <div className="flex flex-wrap gap-1.5">
          {ROLES.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onRole(r.value)}
              className={cn('chip', role === r.value && 'border-radiant/60 bg-radiant/10 text-radiant')}
            >
              {tRoles(r.value)}
            </button>
          ))}
        </div>
      </div>
      <div>
        <label className="label mb-1 block">{t('yourRank')}</label>
        <div className="flex flex-wrap gap-1.5">
          {RANKS.map((r) => (
            <button
              key={r.value}
              type="button"
              onClick={() => onRank(r.value)}
              className={cn('chip', rank === r.value && 'border-radiant/60 bg-radiant/10 text-radiant')}
            >
              {tRanks(String(r.value))}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
