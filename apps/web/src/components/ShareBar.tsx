'use client';

import { useState } from 'react';
import { Check, Loader2, Share2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import { track } from '@/lib/analytics';

/**
 * Share the win plan.
 *
 * The shared link opens a public page that renders the *actual* plan, so the
 * recipient sees value immediately rather than a screenshot. Creating the link
 * spends the sharer's normal daily quota (re-sharing the same draft is free),
 * which keeps the loop from becoming a free-tier bypass.
 */
export function ShareBar({
  enemyIds,
  role,
  rank,
  onQuota,
}: {
  enemyIds: number[];
  role?: string;
  rank?: number;
  onQuota?: () => void;
}) {
  const t = useTranslations('share');
  const [state, setState] = useState<'idle' | 'busy' | 'done' | 'error'>('idle');
  const [copied, setCopied] = useState(false);

  const doShare = async () => {
    if (state === 'busy') return;
    setState('busy');
    setCopied(false);
    let url: string;
    try {
      const res = await api.createShare(enemyIds, role, rank);
      // No signing key on the server (free-only deployment) means no public
      // render endpoint exists, so share the app itself rather than a dead link.
      url = res.path ? `${window.location.origin}${res.path}` : window.location.href;
    } catch (e) {
      setState('error');
      if (e instanceof ApiError && e.status === 402) onQuota?.();
      return;
    }

    track('share_clicked', { heroes: enemyIds.length });
    try {
      if (navigator.share) {
        await navigator.share({ title: 'DraftMaster AI — my win plan', url });
        setState('done');
      } else {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setState('done');
      }
    } catch {
      // The user dismissed the share sheet — not an error worth surfacing.
      setState('idle');
    }
  };

  const label = state === 'busy' ? t('busy') : copied ? t('copied') : state === 'done' ? t('shared') : t('cta');

  return (
    <button
      type="button"
      onClick={doShare}
      disabled={state === 'busy' || enemyIds.length === 0}
      className="btn-ghost !py-1.5 text-xs"
      title={t('hint')}
    >
      {state === 'busy' ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
      ) : copied || state === 'done' ? (
        <Check className="h-3.5 w-3.5 text-radiant" />
      ) : (
        <Share2 className="h-3.5 w-3.5" />
      )}
      {label}
    </button>
  );
}
