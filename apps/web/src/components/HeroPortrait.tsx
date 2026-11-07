'use client';

import { useState } from 'react';
import { cdn, cn } from '@/lib/format';

type Props = {
  icon?: string | null;
  name: string;
  size?: number;
  className?: string;
  priority?: boolean;
};

/**
 * Hero portrait with a graceful fallback. Uses a plain <img> so the browser can
 * cache Valve's CDN images across the whole app without Next image routing.
 */
export function HeroPortrait({ icon, name, size = 44, className, priority }: Props) {
  const [failed, setFailed] = useState(false);
  const src = cdn(icon);
  const initials = name
    .split(/[\s'-]/)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <span
      className={cn(
        'relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-md border border-base-600 bg-base-800',
        className,
      )}
      style={{ width: size, height: size }}
      title={name}
    >
      {src && !failed ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={name}
          width={size}
          height={size}
          loading={priority ? 'eager' : 'lazy'}
          decoding="async"
          onError={() => setFailed(true)}
          className="h-full w-full object-cover"
        />
      ) : (
        <span className="text-[10px] font-bold text-slate-400">{initials}</span>
      )}
    </span>
  );
}
