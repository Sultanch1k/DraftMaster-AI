'use client';

import { useEffect } from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Catches errors thrown above the root layout (e.g. a failed locale message
 * load). Must render its own <html>/<body>, and the intl provider is not
 * available here, so the copy is intentionally static and bilingual.
 */
export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang="en" className="dark">
      <body className="flex min-h-dvh items-center justify-center bg-base-950 px-6 text-center text-ink-soft">
        <div className="flex max-w-lg flex-col items-center gap-4">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-dire/15 text-dire">
            <AlertCircle className="h-6 w-6" />
          </span>
          <h1 className="text-xl font-bold text-ink">DraftMaster AI</h1>
          <p className="text-sm text-ink-muted">
            Something went wrong. Please try again. · Что-то пошло не так. Попробуйте ещё раз.
          </p>
          <button
            type="button"
            onClick={reset}
            className="rounded-lg bg-radiant px-4 py-2.5 text-sm font-semibold text-ink"
          >
            Retry · Повторить
          </button>
        </div>
      </body>
    </html>
  );
}
