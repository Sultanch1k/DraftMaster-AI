'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Loader2, Share2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import { track } from '@/lib/analytics';

/**
 * Mint the signed share token once per draft and return its path (or null).
 *
 * The shared link opens a public page that renders the *actual* plan, so the
 * recipient sees value immediately rather than a screenshot. Creating the link
 * spends the sharer's normal daily quota (re-sharing the same draft is free),
 * which keeps the loop from becoming a free-tier bypass.
 *
 * The same signed token is what the server-side poster renderer consumes, so
 * minting it here serves both the share button and the poster — the poster then
 * never re-charges quota.
 */
export function useShareLink(enemyIds: number[], role?: string, rank?: number) {
  const [path, setPath] = useState<string | null>(null);
  const key = `${enemyIds.join(',')}|${role ?? ''}|${rank ?? ''}`;
  const minted = useRef<string | null>(null);

  useEffect(() => {
    if (enemyIds.length === 0) return;
    if (minted.current === key) return;
    minted.current = key;
    let live = true;
    api
      .createShare(enemyIds, role, rank)
      .then((res) => {
        if (live) setPath(res.path || null);
      })
      .catch(() => {
        // 402/network: no token. The poster degrades to the client share flow.
        if (live) setPath(null);
      });
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return path;
}

/**
 * Share the win plan.
 *
 * When the parent has already minted a token (via `useShareLink`) it is reused,
 * so the share button never spends a second quota unit on the same draft.
 */
export function ShareBar({
  enemyIds,
  role,
  rank,
  onQuota,
  token,
}: {
  enemyIds: number[];
  role?: string;
  rank?: number;
  onQuota?: () => void;
  /** A token already minted by the parent, to avoid a second quota charge. */
  token?: string | null;
}) {
  const t = useTranslations('share');
  const [state, setState] = useState<'idle' | 'busy' | 'done' | 'error'>('idle');
  const [copied, setCopied] = useState(false);

  const doShare = useCallback(async () => {
    if (state === 'busy') return;
    setState('busy');
    setCopied(false);
    let url: string;
    try {
      const path = token ?? (await api.createShare(enemyIds, role, rank)).path;
      // No signing key on the server (free-only deployment) means no public
      // render endpoint exists, so share the app itself rather than a dead link.
      url = path ? `${window.location.origin}${path}` : window.location.href;
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
  }, [state, token, enemyIds, role, rank, onQuota]);

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
