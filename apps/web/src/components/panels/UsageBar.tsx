'use client';

import type { Usage } from '@/lib/types';
import { cn } from '@/lib/format';

export function UsageBar({ premium, usage }: { premium: boolean; usage?: Usage }) {
  const limit = usage?.daily_limit ?? 3;
  const used = usage?.used_today ?? 0;
  const remaining = usage?.remaining ?? Math.max(0, limit - used);
  const pct = premium ? 100 : Math.min(100, (used / limit) * 100);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-400">{premium ? 'Premium · unlimited' : 'Free plan'}</span>
        {!premium && (
          <span className={cn('tabular-nums', remaining === 0 ? 'text-dire' : 'text-slate-400')}>
            {remaining} of {limit} left today
          </span>
        )}
      </div>
      <div className="bar">
        <div
          className={cn('h-full rounded-full transition-all', premium ? 'bg-gold' : remaining === 0 ? 'bg-dire' : 'bg-radiant')}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
