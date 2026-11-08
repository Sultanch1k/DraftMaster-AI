'use client';

import { Check, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/format';

/**
 * Upgrade / plan panel. Billing is not wired yet, so "activate" turns on the
 * in-app Premium state directly; the copy is honest about it being early access
 * rather than a checkout flow.
 */
export function PremiumModal({
  open,
  premium,
  onClose,
  onToggle,
}: {
  open: boolean;
  premium: boolean;
  onClose: () => void;
  onToggle: () => void;
}) {
  const t = useTranslations('premium');
  if (!open) return null;

  const plans = [
    { key: 'free', features: [t('free1'), t('free2'), t('free3')] },
    { key: 'pro', features: [t('pro1'), t('pro2'), t('pro3'), t('pro4')] },
  ] as const;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div className="card card-pad w-full max-w-lg" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="section-title">{t('title')}</h2>
          <button type="button" onClick={onClose} aria-label={t('close')} className="rounded p-1 text-slate-400 hover:text-slate-200">
            <X className="h-4 w-4" />
          </button>
        </div>
        <p className="mb-4 text-sm text-slate-400">{t('subtitle')}</p>

        <div className="grid gap-3 sm:grid-cols-2">
          {plans.map((p) => {
            const active = p.key === 'pro' ? premium : !premium;
            return (
              <div
                key={p.key}
                className={cn(
                  'flex flex-col gap-3 rounded-xl border p-4',
                  active ? 'border-radiant bg-radiant/5' : 'border-base-700 bg-base-850/60',
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white">{t(p.key)}</span>
                  {active && <span className="chip border-radiant/50 text-radiant">{t('current')}</span>}
                </div>
                <p className="text-xs text-slate-400">{t(`${p.key}Price`)}</p>
                <ul className="flex flex-1 flex-col gap-1.5">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-xs text-slate-300">
                      <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-radiant" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>

        <p className="mt-3 text-[11px] text-slate-500">{t('note')}</p>

        <button type="button" onClick={onToggle} className="btn-primary mt-4 w-full">
          {premium ? t('downgrade') : t('activate')}
        </button>
      </div>
    </div>
  );
}
