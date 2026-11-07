'use client';

import { cn } from '@/lib/format';

export type TabKey = 'lastpick' | 'draft' | 'screenshot' | 'coach' | 'meta';

const TABS: { key: TabKey; label: string; icon: string; accent?: string }[] = [
  { key: 'lastpick', label: "I'M LAST PICK", icon: '🚨', accent: 'dire' },
  { key: 'draft', label: 'Full Report', icon: '📊' },
  { key: 'screenshot', label: 'Screenshot', icon: '🖼️' },
  { key: 'coach', label: 'Match Coach', icon: '🎯' },
  { key: 'meta', label: 'Meta Intel', icon: '📈' },
];

export function Header({
  tab,
  onTab,
  patch,
  premium,
  onPremium,
}: {
  tab: TabKey;
  onTab: (t: TabKey) => void;
  patch?: string | null;
  premium: boolean;
  onPremium: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-base-700 bg-base-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-3 py-2.5 sm:px-5">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-radiant to-radiant-dim text-base-950">
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden>
              <path d="M12 2 3 6v6c0 5 3.8 9.3 9 10 5.2-.7 9-5 9-10V6l-9-4Zm0 4.2 5 2.2v3.6c0 3.4-2.2 6.3-5 7-2.8-.7-5-3.6-5-7V8.4l5-2.2Z" />
            </svg>
          </span>
          <div className="leading-tight">
            <p className="text-sm font-black tracking-tight text-white">
              DraftMaster<span className="text-radiant"> AI</span>
            </p>
            <p className="hidden text-[10px] text-slate-500 sm:block">
              Here is exactly how to win this specific game
            </p>
          </div>
        </div>

        <nav className="ml-auto flex items-center gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => onTab(t.key)}
              className={cn(
                'shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition',
                tab === t.key
                  ? t.accent === 'dire'
                    ? 'bg-dire text-white'
                    : 'bg-base-700 text-white'
                  : 'text-slate-400 hover:bg-base-800 hover:text-slate-200',
              )}
            >
              <span className="mr-1">{t.icon}</span>
              <span className="hidden sm:inline">{t.label}</span>
            </button>
          ))}
        </nav>

        <div className="ml-1 hidden items-center gap-2 md:flex">
          {patch && <span className="chip">Patch {patch}</span>}
          <button
            type="button"
            onClick={onPremium}
            className={cn('chip', premium ? 'border-gold/60 text-gold' : 'border-base-600')}
            title="Toggle Premium (demo): unlimited analyses + AI coach"
          >
            {premium ? '★ Premium' : 'Free plan'}
          </button>
        </div>
      </div>
    </header>
  );
}
