'use client';

import { useCallback, useMemo, useState } from 'react';
import { Check, Copy, Download, Loader2, Share2 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { cn } from '@/lib/format';
import { track } from '@/lib/analytics';

type Format = 'story' | 'square' | 'portrait';

const FORMATS: { key: Format; ratio: string; labelKey: string }[] = [
  { key: 'story', ratio: '9:16', labelKey: 'story' },
  { key: 'square', ratio: '1:1', labelKey: 'square' },
  { key: 'portrait', ratio: '4:5', labelKey: 'portrait' },
];

/**
 * Viral social export.
 *
 * The poster is rendered by the server (`/api/poster` or `/api/share-poster`) as
 * a real PNG with embedded hero art, so this component only has to present,
 * download and share it. Share order: native file share where available (posts
 * straight to the story), then a plain download plus a copied caption.
 */
export function PosterExport({
  posterBase,
  filename,
  caption,
}: {
  /** Poster endpoint path without the `format`/`locale` query, e.g. `/api/poster?e=1,2`. */
  posterBase: string;
  /** Base filename (without extension) for downloads. */
  filename: string;
  /** Ready-to-post caption text. */
  caption: string;
}) {
  const t = useTranslations('winplan.share');
  const locale = useLocale();
  const [format, setFormat] = useState<Format>('story');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState<'link' | 'caption' | null>(null);

  const sep = posterBase.includes('?') ? '&' : '?';
  const url = useMemo(
    () => `${posterBase}${sep}locale=${locale}&format=${format}`,
    [posterBase, sep, locale, format],
  );

  const fetchBlob = useCallback(async (): Promise<Blob | null> => {
    try {
      const res = await fetch(url);
      if (!res.ok) return null;
      return await res.blob();
    } catch {
      return null;
    }
  }, [url]);

  const download = useCallback(async () => {
    setBusy(true);
    const blob = await fetchBlob();
    if (blob) {
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href;
      a.download = `${filename}-${format}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
      track('poster_downloaded', { format });
    }
    setBusy(false);
  }, [fetchBlob, filename, format]);

  const share = useCallback(async () => {
    setBusy(true);
    const blob = await fetchBlob();
    const shareUrl = `${window.location.origin}${posterBase}${sep}locale=${locale}&format=${format}`;
    try {
      if (blob) {
        const file = new File([blob], `${filename}.png`, { type: 'image/png' });
        if (navigator.canShare?.({ files: [file] })) {
          await navigator.share({ files: [file], text: caption });
          track('poster_shared', { format, method: 'file' });
          setBusy(false);
          return;
        }
      }
      if (navigator.share) {
        await navigator.share({ title: 'DraftMaster AI', text: caption, url: shareUrl });
        track('poster_shared', { format, method: 'native' });
      } else {
        await navigator.clipboard.writeText(`${caption}\n\n${shareUrl}`);
        setCopied('caption');
        track('poster_shared', { format, method: 'clipboard' });
      }
    } catch {
      // Share sheet dismissed — nothing to surface.
    }
    setBusy(false);
  }, [fetchBlob, caption, filename, format, locale, posterBase, sep]);

  const copy = useCallback(
    async (what: 'link' | 'caption') => {
      const text =
        what === 'link' ? `${window.location.origin}${url}` : `${caption}\n\n${window.location.origin}${url}`;
      try {
        await navigator.clipboard.writeText(text);
        setCopied(what);
        setTimeout(() => setCopied(null), 2000);
      } catch {
        /* clipboard unavailable */
      }
    },
    [caption, url],
  );

  return (
    <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <p className="kicker">{t('title')}</p>
          <p className="mt-1 text-xs text-ink-faint">{t('subtitle')}</p>
        </div>
      </div>

      <div className="mb-3 flex gap-1.5">
        {FORMATS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => setFormat(f.key)}
            className={cn(
              'rounded-lg border px-3 py-1.5 text-xs font-semibold transition',
              format === f.key
                ? 'border-accent/60 bg-accent/15 text-accent-bright'
                : 'border-base-600 bg-base-800/60 text-ink-muted hover:bg-base-700',
            )}
          >
            {t(f.labelKey)} <span className="tabular ml-1 text-[10px] text-ink-faint">{f.ratio}</span>
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-base-700 bg-base-900">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt={t('previewAlt')}
          className={cn('mx-auto w-full object-contain', format === 'story' ? 'max-h-[420px]' : 'max-h-[360px]')}
          loading="lazy"
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <button type="button" onClick={share} disabled={busy} className="btn-primary !py-2 text-xs">
          {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Share2 className="h-3.5 w-3.5" />}
          {t('share')}
        </button>
        <button type="button" onClick={download} disabled={busy} className="btn-ghost !py-2 text-xs">
          <Download className="h-3.5 w-3.5" />
          {t('download')}
        </button>
        <button type="button" onClick={() => copy('link')} className="btn-ghost !py-2 text-xs">
          {copied === 'link' ? <Check className="h-3.5 w-3.5 text-radiant" /> : <Copy className="h-3.5 w-3.5" />}
          {copied === 'link' ? t('copied') : t('copyLink')}
        </button>
        <button type="button" onClick={() => copy('caption')} className="btn-ghost !py-2 text-xs">
          {copied === 'caption' ? <Check className="h-3.5 w-3.5 text-radiant" /> : <Copy className="h-3.5 w-3.5" />}
          {copied === 'caption' ? t('copied') : t('copyCaption')}
        </button>
      </div>
    </section>
  );
}
