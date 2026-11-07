'use client';

import { useTransition } from 'react';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/format';
import { isLocale, locales, LOCALE_LABELS, type Locale } from '@/i18n/config';

/**
 * Compact EN/RU toggle. Persists the choice in a cookie, then refreshes the
 * server components so the new locale is applied on the next render.
 */
export function LocaleSwitcher({ className }: { className?: string }) {
  const active = useLocale();
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  const choose = (locale: Locale) => {
    if (locale === active || pending) return;
    startTransition(async () => {
      await fetch('/locale', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale }),
      });
      router.refresh();
    });
  };

  return (
    <div
      className={cn('flex items-center gap-0.5 rounded-lg border border-base-600 bg-base-800/60 p-0.5', className)}
      role="group"
    >
      {locales.map((locale) => {
        const selected = isLocale(active) && active === locale;
        return (
          <button
            key={locale}
            type="button"
            onClick={() => choose(locale)}
            aria-pressed={selected}
            className={cn(
              'rounded px-1.5 py-0.5 text-[11px] font-bold transition',
              selected ? 'bg-base-600 text-white' : 'text-slate-400 hover:text-slate-200',
            )}
          >
            {LOCALE_LABELS[locale]}
          </button>
        );
      })}
    </div>
  );
}
