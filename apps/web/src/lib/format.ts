import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CDN = 'https://cdn.cloudflare.steamstatic.com';

export function cdn(path?: string | null): string {
  if (!path) return '';
  const clean = path.split('?')[0];
  return `${CDN}${clean}`;
}

export function dangerColor(level?: string): string {
  switch (level) {
    case 'high':
      return 'text-dire';
    case 'medium':
      return 'text-gold';
    default:
      return 'text-radiant';
  }
}

export function dangerBg(level?: string): string {
  switch (level) {
    case 'high':
      return 'bg-dire';
    case 'medium':
      return 'bg-gold';
    default:
      return 'bg-radiant';
  }
}

/** Maps a 0-100 score onto a green/amber/red scale used across the UI. */
export function scoreColor(score: number): string {
  if (score >= 70) return 'text-radiant';
  if (score >= 55) return 'text-gold';
  return 'text-dire';
}

export function scoreBar(score: number): string {
  if (score >= 70) return 'bg-radiant';
  if (score >= 55) return 'bg-gold';
  return 'bg-dire';
}

export function pct(n: number, digits = 1): string {
  return `${n.toFixed(digits)}%`;
}

export function clamp(n: number, min = 0, max = 100): number {
  return Math.max(min, Math.min(max, n));
}

export const ROLES = [
  { value: 'carry', label: 'Carry (1)' },
  { value: 'mid', label: 'Mid (2)' },
  { value: 'offlane', label: 'Offlane (3)' },
  { value: 'support', label: 'Support (4)' },
  { value: 'hard_support', label: 'Hard Support (5)' },
] as const;

export const RANKS = [
  { value: 11, label: 'Herald' },
  { value: 22, label: 'Guardian' },
  { value: 33, label: 'Crusader' },
  { value: 44, label: 'Archon' },
  { value: 55, label: 'Legend' },
  { value: 66, label: 'Ancient' },
  { value: 77, label: 'Divine' },
  { value: 80, label: 'Immortal' },
] as const;

export const ROLE_FILTERS = ['Carry', 'Support', 'Nuker', 'Initiator', 'Disabler', 'Durable', 'Escape', 'Pusher', 'Jungler'] as const;
