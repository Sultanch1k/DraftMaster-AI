'use client';

import { useTranslations } from 'next-intl';
import { cn } from '@/lib/format';
import { LocaleSwitcher } from './LocaleSwitcher';

export type TabKey = 'lastpick' | 'draft' | 'screenshot' | 'coach' | 'meta';

const TABS: { key: TabKey; icon: string; accent?: string }[] = [
  { key: 'lastpick', icon: '🚨', accent: 'dire' },
  { key: 'draft', icon: '📊' },
  { key: 'screenshot', icon: '🖼️' },
  { key: 'coach', icon: '🎯' },
  { key: 'meta', icon: '📈' },
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
  const t = useTranslations('header');
  const tTabs = useTranslations('tabs');

  return (
    <header className="sticky top-0 z-30 border-b border-base-700 bg-base-950/85 backdrop-blur">
      <div className="mx-auto flex max-w-[1600px] items-center gap-3 px-3 py-2.5 sm:px-6">
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
            <p className="hidden text-[10px] text-slate-500 sm:block">{t('tagline')}</p>
          </div>
        </div>

        <nav className="ml-auto flex items-center gap-1 overflow-x-auto">
          {TABS.map((tab_) => (
            <button
              key={tab_.key}
              type="button"
              onClick={() => onTab(tab_.key)}
              className={cn(
                'shrink-0 rounded-lg px-2.5 py-1.5 text-xs font-semibold transition',
                tab === tab_.key
                  ? tab_.accent === 'dire'
                    ? 'bg-dire text-white'
                    : 'bg-base-700 text-white'
                  : 'text-slate-400 hover:bg-base-800 hover:text-slate-200',
              )}
            >
              <span className="mr-1">{tab_.icon}</span>
              <span className="hidden sm:inline">{tTabs(tab_.key)}</span>
            </button>
          ))}
        </nav>

        <div className="ml-1 flex items-center gap-2">
          {patch && <span className="chip hidden lg:inline-flex">{t('patch', { patch })}</span>}
          <button
            type="button"
            onClick={onPremium}
            className={cn('chip hidden md:inline-flex', premium ? 'border-gold/60 text-gold' : 'border-base-600')}
            title={t('premiumTitle')}
          >
            {premium ? t('premium') : t('free')}
          </button>
          <LocaleSwitcher />
        </div>
      </div>
    </header>
  );
}
