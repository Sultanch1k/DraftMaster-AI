'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowRight, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import { installAnalytics, track } from '@/lib/analytics';
import type { PanicResult } from '@/lib/types';
import { PanicView } from './PanicView';

/**
 * Public view of a shared win plan.
 *
 * The token is signed by the server, so this renders a real plan for anyone who
 * opens the link — including someone who has never used the product. The only
 * call to action is "get your own plan", which is the whole point of the loop.
 */
export function ShareView({ token }: { token: string }) {
  const t = useTranslations('share');
  const [result, setResult] = useState<PanicResult | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    installAnalytics();
    track('share_opened', {});
    api
      .renderShare(token)
      .then(setResult)
      .catch((e) => {
        // A 404 means the token is forged or expired; anything else is transient.
        if (e instanceof ApiError && e.status === 404) setFailed(true);
        else setFailed(true);
      });
  }, [token]);

  if (failed) {
    return (
      <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-24 text-center">
        <p className="text-lg font-semibold text-slate-200">{t('invalid')}</p>
        <Link href="/" className="btn-primary">
          {t('ctaOwn')} <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex items-center justify-center gap-3 py-24 text-sm text-slate-400">
        <Loader2 className="h-5 w-5 animate-spin text-radiant" />
        {t('loading')}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="card card-pad border-radiant/40">
        <p className="text-sm font-semibold text-radiant">{t('viewTitle')}</p>
        <p className="mt-1 text-xs text-slate-400">{t('viewSub')}</p>
        <Link href="/" className="btn-primary mt-3 self-start">
          {t('ctaOwn')} <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
      <PanicView result={result} />
      <p className="text-center text-xs text-slate-500">{t('madeBy')}</p>
    </div>
  );
}
