'use client';

import { Check, Loader2, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useEffect, useState } from 'react';
import { api, ApiError, setSessionToken } from '@/lib/api';
import { track } from '@/lib/analytics';
import { cn } from '@/lib/format';
import type { BillingConfig } from '@/lib/types';

/**
 * Upgrade / plan panel.
 *
 * The purchase path is intentionally the shortest possible: the buy button
 * opens the hosted Lemon Squeezy checkout in a new tab, and after paying the
 * user pastes the license key they receive by email to unlock premium. No
 * account, no password — the smallest gap between "wants it" and "has it".
 *
 * When billing is not yet configured (no keys on the server) the panel shows
 * the free plan only and hides the buy button rather than linking to a dead
 * checkout.
 */
export function PremiumModal({
  open,
  premium,
  onClose,
  onActivated,
}: {
  open: boolean;
  premium: boolean;
  onClose: () => void;
  onActivated: () => void;
}) {
  const t = useTranslations('premium');
  const [config, setConfig] = useState<BillingConfig | null>(null);
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);
  const [email, setEmail] = useState('');
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailDone, setEmailDone] = useState(false);
  const [emailError, setEmailError] = useState('');

  useEffect(() => {
    if (!open) return;
    api.billingConfig().then(setConfig).catch(() => setConfig(null));
  }, [open]);

  if (!open) return null;

  // Never take money we cannot fulfil: the purchase block only appears when the
  // server can both sell (checkout URL) and activate (provider API credentials).
  const sellable = Boolean(config?.enabled && config?.checkout_url);
  const checkoutUrl = config?.checkout_url || '';

  async function subscribe() {
    const value = email.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value)) {
      setEmailError(t('emailInvalid'));
      return;
    }
    setEmailBusy(true);
    setEmailError('');
    try {
      await api.subscribeEmail(value);
      track('email_captured', { source: 'paywall' });
      setEmailDone(true);
    } catch {
      setEmailError(t('emailInvalid'));
    } finally {
      setEmailBusy(false);
    }
  }

  async function activate() {
    setBusy(true);
    setError('');
    try {
      const session = await api.activate(key.trim());
      if (session.token) {
        setSessionToken(session.token);
        track('license_activated', { plan: session.plan });
        setDone(true);
        onActivated();
      } else {
        setError(t('activateFailed'));
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('activateFailed'));
    } finally {
      setBusy(false);
    }
  }

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
      <div className="card card-pad max-h-[92dvh] w-full max-w-lg overflow-y-auto" onClick={(e) => e.stopPropagation()}>
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

        {!premium && (
          <div className="mt-4 flex flex-col gap-3 rounded-xl border border-base-700 bg-base-900/60 p-3">
            {done ? (
              <p className="text-sm font-semibold text-radiant">{t('activated')}</p>
            ) : sellable ? (
              <>
                <a
                  href={checkoutUrl}
                  target="_blank"
                  rel="noreferrer noopener"
                  onClick={() => track('checkout_opened', {})}
                  className="btn-primary w-full text-center"
                >
                  {t('buy')}
                </a>
                <p className="text-[11px] text-slate-500">{t('afterPurchase')}</p>
                <div className="flex gap-2">
                  <input
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                    placeholder={t('licensePlaceholder')}
                    autoComplete="off"
                    spellCheck={false}
                    className="w-full rounded-lg border border-base-600 bg-base-900/80 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-radiant/60"
                  />
                  <button type="button" onClick={activate} disabled={busy || key.trim().length < 4} className="btn-primary shrink-0">
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : t('activate')}
                  </button>
                </div>
                {error && <p className="text-xs text-dire">{error}</p>}
              </>
            ) : (
              <p className="text-[11px] text-slate-500">{t('comingSoon')}</p>
            )}
          </div>
        )}

        {!premium && !emailDone && (
          <div className="mt-3 rounded-xl border border-base-800 bg-base-900/40 p-3">
            <p className="text-xs font-semibold text-slate-200">{t('emailTitle')}</p>
            <p className="mt-1 text-[11px] text-slate-500">{t('emailBody')}</p>
            <div className="mt-2 flex gap-2">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t('emailPlaceholder')}
                autoComplete="email"
                className="w-full rounded-lg border border-base-600 bg-base-900/80 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-radiant/60"
              />
              <button type="button" onClick={subscribe} disabled={emailBusy} className="btn-ghost shrink-0 border border-base-600">
                {emailBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : t('emailCta')}
              </button>
            </div>
            {emailError && <p className="mt-1 text-xs text-dire">{emailError}</p>}
          </div>
        )}
        {emailDone && <p className="mt-3 text-xs font-semibold text-radiant">{t('emailDone')}</p>}

        <p className="mt-3 text-[11px] text-slate-500">{t('note')}</p>
      </div>
    </div>
  );
}
