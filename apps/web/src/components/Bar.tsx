import { cn, scoreBar, scoreColor } from '@/lib/format';

export function Bar({ value, className }: { value: number; className?: string }) {
  return (
    <div className={cn('bar', className)}>
      <div className={cn('h-full rounded-full transition-all', scoreBar(value))} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}

export function StatRow({ label, value, suffix = '' }: { label: string; value: number; suffix?: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 shrink-0 text-xs text-slate-400">{label}</span>
      <Bar value={value} className="flex-1" />
      <span className={cn('w-14 shrink-0 text-right text-xs font-semibold tabular-nums', scoreColor(value))}>
        {value.toFixed(1)}
        {suffix}
      </span>
    </div>
  );
}
