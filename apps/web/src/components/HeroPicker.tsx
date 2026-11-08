'use client';

import { memo, useMemo, useState } from 'react';
import { Search, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { Hero } from '@/lib/types';
import { cn, ROLE_FILTERS } from '@/lib/format';
import { HeroPortrait } from './HeroPortrait';

type Props = {
  heroes: Hero[];
  selected: number[];
  onToggle: (id: number) => void;
  /** At most one hero may be selected — used for the "my hero" picker. */
  single?: boolean;
  /** Heroes already used elsewhere, so the same hero cannot be picked twice. */
  disabledIds?: number[];
};

/**
 * Hero picker for My Hero Strategy, using the same search + role filter
 * interaction as the enemy grid so the two feel like one product. Handles both
 * the single-select "my hero" case and the five-slot enemy case.
 */
export const HeroPicker = memo(function HeroPicker({ heroes, selected, onToggle, single, disabledIds = [] }: Props) {
  const t = useTranslations('draft');
  const [query, setQuery] = useState('');
  const [role, setRole] = useState<string | null>(null);

  const disabled = useMemo(() => new Set(disabledIds), [disabledIds]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return heroes.filter((h) => {
      if (role && !h.roles.includes(role)) return false;
      if (!q) return true;
      return (
        h.localized_name.toLowerCase().includes(q) ||
        h.name.replace('npc_dota_hero_', '').replace(/_/g, ' ').includes(q)
      );
    });
  }, [heroes, query, role]);

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t('searchPlaceholder')}
          autoComplete="off"
          spellCheck={false}
          className="w-full rounded-lg border border-base-600 bg-base-900/80 py-2.5 pl-9 pr-9 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-radiant/60 focus:ring-1 focus:ring-radiant/40"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            aria-label={t('clearSearch')}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-200"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1">
        <button
          type="button"
          onClick={() => setRole(null)}
          className={cn('chip shrink-0', !role && 'border-radiant/60 bg-radiant/10 text-radiant')}
        >
          {t('all')}
        </button>
        {ROLE_FILTERS.map((r) => (
          <button
            key={r}
            type="button"
            onClick={() => setRole(role === r ? null : r)}
            className={cn('chip shrink-0', role === r && 'border-radiant/60 bg-radiant/10 text-radiant')}
          >
            {r}
          </button>
        ))}
      </div>

      <div className="grid max-h-[min(40vh,320px)] grid-cols-5 gap-1.5 overflow-y-auto pr-1 sm:grid-cols-8 md:grid-cols-10 lg:grid-cols-12">
        {filtered.map((h) => {
          const isSelected = selectedSet.has(h.id);
          const atCapacity = single ? selected.length > 0 && !isSelected : selected.length >= 5 && !isSelected;
          const isDisabled = atCapacity || (disabled.has(h.id) && !isSelected);
          return (
            <button
              key={h.id}
              type="button"
              onClick={() => onToggle(h.id)}
              disabled={isDisabled}
              title={h.localized_name}
              aria-pressed={isSelected}
              className={cn(
                'group relative flex flex-col items-center gap-1 rounded-lg border p-1 transition',
                isSelected
                  ? 'border-radiant bg-radiant/15 shadow-glow'
                  : 'border-base-700 bg-base-850/60 hover:border-base-600 hover:bg-base-800',
                isDisabled && 'cursor-not-allowed opacity-30 hover:border-base-700',
              )}
            >
              <HeroPortrait icon={h.icon} name={h.localized_name} size={44} />
              <span className="w-full truncate text-center text-[10px] leading-tight text-slate-400 group-hover:text-slate-200">
                {h.localized_name}
              </span>
              {isSelected && (
                <span className="absolute right-0.5 top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-radiant text-[9px] font-bold text-base-950">
                  ✓
                </span>
              )}
            </button>
          );
        })}
        {filtered.length === 0 && (
          <p className="col-span-full py-8 text-center text-sm text-slate-500">{t('noMatch', { query })}</p>
        )}
      </div>
    </div>
  );
});
