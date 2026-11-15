'use client';

import { useCallback, useEffect, useState } from 'react';
import { Check, Copy, Download, Loader2, Share2, Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import { cn } from '@/lib/format';
import { track } from '@/lib/analytics';
import { PosterExport } from './winplan/PosterExport';

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
export function useShareLink(enemyIds: number[], role?: string, rank?: number, heroId?: number) {
  const [path, setPath] = useState<string | null>(null);
  const key = `${enemyIds.join(',')}|${role ?? ''}|${rank ?? ''}|${heroId ?? ''}`;

  useEffect(() => {
    if (enemyIds.length === 0) return;
    let live = true;
    api
      .createShare(enemyIds, role, rank, heroId)
      .then((res) => {
        if (live) setPath(res.path || null);
      })
      .catch(() => {
        // 402/network: no token. Sharing degrades to the app URL.
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
 * "Share with friends" — the prominent sharing experience on a win plan.
 *
 * This is a first-class panel, not a footnote: the whole growth loop depends on
 * a player who just got value being able to hand it to a friend in one obvious
 * action. It offers copy-link, native share sheet, and the designed poster
 * downloads, and it always tells the user what happened.
 */
export function ShareWithFriends({
  enemyIds,
  role,
  rank,
  heroName,
  winPlan,
  token,
  heroId,
  onQuota,
}: {
  enemyIds: number[];
  role?: string;
  rank?: number;
  heroName: string;
  winPlan: string;
  /** Set for My Hero shares so the token encodes the strategy mode. */
  heroId?: number;
  /** A token already minted by the parent, to avoid a second quota charge. */
  token?: string | null;
  onQuota?: () => void;
}) {
  const t = useTranslations('sharebox');
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [showPoster, setShowPoster] = useState(false);

  const caption = t('caption', { hero: heroName, plan: winPlan });

  const resolveLink = useCallback(async (): Promise<string | null> => {
    if (link) return link;
    try {
      const path = token ?? (await api.createShare(enemyIds, role, rank, heroId)).path;
      const url = path ? `${window.location.origin}${path}` : window.location.href;
      setLink(url);
      return url;
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) onQuota?.();
      setNote(t('linkUnavailable'));
      return null;
    }
  }, [link, token, enemyIds, role, rank, heroId, onQuota, t]);

  const copy = useCallback(async () => {
    setBusy(true);
    setNote(null);
    const url = await resolveLink();
    if (url) {
      try {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setNote(t('copied'));
        track('share_link_copied', { heroes: enemyIds.length });
        setTimeout(() => setCopied(false), 2500);
      } catch {
        setNote(url);
      }
    }
    setBusy(false);
  }, [resolveLink, t, enemyIds.length]);

  const nativeShare = useCallback(async () => {
    setBusy(true);
    setNote(null);
    const url = await resolveLink();
    if (url) {
      if (navigator.share) {
        try {
          await navigator.share({ title: 'DraftMaster AI', text: caption, url });
          track('share_native', { heroes: enemyIds.length });
        } catch {
          // The user dismissed the share sheet — not an error worth surfacing.
        }
      } else {
        try {
          await navigator.clipboard.writeText(url);
          setCopied(true);
          setNote(t('noNative'));
          setTimeout(() => setCopied(false), 2500);
        } catch {
          setNote(url);
        }
      }
    }
    setBusy(false);
  }, [resolveLink, caption, t, enemyIds.length]);

  const posterBase = link && link.includes('/share/')
    ? `${new URL(link).pathname.replace(/^\/share\//, '/og/share/')}`
    : token
      ? `/og/share/${encodeURIComponent(token)}`
      : null;

  return (
    <section className="relative overflow-hidden rounded-panel border border-accent/40 bg-gradient-to-br from-accent/10 via-base-850 to-base-850 p-4 sm:p-5">
      <div className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full bg-accent/10 blur-3xl" aria-hidden />
      <div className="relative flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-3">
          <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent/15 text-accent-bright">
            <Sparkles className="h-5 w-5" />
          </span>
          <div>
            <p className="kicker">{t('kicker')}</p>
            <h3 className="mt-1 text-lg font-black text-ink">{t('title')}</h3>
            <p className="mt-1 max-w-lg text-xs leading-relaxed text-ink-muted sm:text-sm">{t('body')}</p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={copy} disabled={busy} className="btn-primary">
            {busy ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : copied ? (
              <Check className="h-4 w-4" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
            {copied ? t('copied') : t('copyLink')}
          </button>
          <button type="button" onClick={nativeShare} disabled={busy} className="btn-ghost">
            <Share2 className="h-4 w-4" />
            {t('share')}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowPoster((v) => !v);
              track('poster_panel_toggled', { open: !showPoster });
            }}
            className="btn-ghost"
            aria-expanded={showPoster}
          >
            <Download className="h-4 w-4" />
            {t('poster')}
          </button>
        </div>
      </div>

      {note && (
        <p className={cn('relative mt-3 text-xs', copied ? 'text-radiant' : 'text-ink-muted')} role="status">
          {note}
        </p>
      )}

      {showPoster && (
        <div className="relative mt-4">
          {posterBase ? (
            <PosterExport
              posterBase={posterBase}
              filename={`draftmaster-${heroName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
              caption={caption}
            />
          ) : (
            <p className="text-xs text-ink-muted">{t('posterPending')}</p>
          )}
        </div>
      )}
    </section>
  );
}
