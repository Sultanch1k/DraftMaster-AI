'use client';

import { useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { useTranslations } from 'next-intl';

/**
 * Route-level error boundary. Renders inside the root layout, so the intl
 * provider (and therefore localised copy) is available.
 */
export default function Error({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations('errors');

  useEffect(() => {
    // Surface the error in the browser console for debugging; the UI shows a
    // friendly message instead of Next's default crash screen.
    console.error(error);
  }, [error]);

  return (
    <div className="mx-auto flex min-h-dvh max-w-lg flex-col items-center justify-center gap-4 px-6 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-dire/15 text-dire">
        <AlertCircle className="h-6 w-6" />
      </span>
      <h1 className="text-xl font-bold text-white">DraftMaster AI</h1>
      <p className="text-sm text-slate-400">{t('generic')}</p>
      <button type="button" onClick={reset} className="btn-primary">
        {t('retry')}
      </button>
    </div>
  );
}
