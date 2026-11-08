'use client';

import { useEffect, useRef } from 'react';
import { Shield, Swords, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { TabKey } from './Header';

type Props = {
  open: boolean;
  onClose: () => void;
  onPick: (mode: TabKey) => void;
};

/**
 * First-run mode chooser.
 *
 * The product answers two different questions — "which hero should I pick?" and
 * "I already picked; how do I win?" — and players arrive knowing which one they
 * need. Asking once removes the ambiguity of a tab bar for first-time users
 * without adding a step for returning users.
 */
export function ModeChooser({ open, onClose, onPick }: Props) {
  const t = useTranslations('mode');
  const firstRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    firstRef.current?.focus();
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={t('title')}
      className="fixed inset-0 z-50 flex items-center justify-center bg-base-950/80 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl border border-base-700 bg-base-900 p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 className="text-lg font-black text-white">{t('title')}</h2>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded p-1 text-slate-400 hover:text-white">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <button
            ref={firstRef}
            type="button"
            onClick={() => onPick('lastpick')}
            className="group flex flex-col items-start gap-2 rounded-xl border border-base-700 bg-base-850/60 p-4 text-left transition hover:border-dire/60 hover:bg-dire/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-dire/60"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-dire/15 text-dire">
              <Swords className="h-5 w-5" />
            </span>
            <span className="text-sm font-bold text-white">{t('counterTitle')}</span>
            <span className="text-xs leading-relaxed text-slate-400">{t('counterBody')}</span>
          </button>

          <button
            type="button"
            onClick={() => onPick('mystrategy')}
            className="group flex flex-col items-start gap-2 rounded-xl border border-base-700 bg-base-850/60 p-4 text-left transition hover:border-radiant/60 hover:bg-radiant/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-radiant/60"
          >
            <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-radiant/15 text-radiant">
              <Shield className="h-5 w-5" />
            </span>
            <span className="text-sm font-bold text-white">{t('mineTitle')}</span>
            <span className="text-xs leading-relaxed text-slate-400">{t('mineBody')}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
