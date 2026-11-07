import type {
  CoachReport,
  Hero,
  Meta,
  PanicResult,
  Report,
  ScreenshotResult,
  Usage,
} from './types';

// All requests go to the Next.js server, which proxies /api/* to FastAPI.
const BASE = '';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function userId(): string {
  if (typeof window === 'undefined') return 'anonymous';
  let id = window.localStorage.getItem('draftmaster_user');
  if (!id) {
    id = `u_${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem('draftmaster_user', id);
  }
  return id;
}

function premiumHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  return window.localStorage.getItem('draftmaster_premium') === '1'
    ? { authorization: 'Bearer premium-token' }
    : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'x-user-id': userId(),
      ...premiumHeaders(),
      ...(init?.headers || {}),
    },
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  heroes: () => request<Hero[]>('/api/heroes'),
  items: () => request<{ key: string; dname: string; cost?: number }[]>('/api/items'),
  meta: () => request<Meta>('/api/meta'),

  panic: (enemy_hero_ids: number[], role?: string, rank_tier?: number, comfort?: Record<number, number>) =>
    request<PanicResult>('/api/panic', {
      method: 'POST',
      body: JSON.stringify({ enemy_hero_ids, role, rank_tier, comfort }),
    }),

  analyse: (enemy_hero_ids: number[], hero_id?: number, role?: string, rank_tier?: number, comfort?: Record<number, number>) =>
    request<{ report: Report; usage: Usage; cached: boolean }>('/api/analyse', {
      method: 'POST',
      body: JSON.stringify({ enemy_hero_ids, hero_id, role, rank_tier, comfort }),
    }),

  winProbability: (enemy_hero_ids: number[], hero_id: number, role?: string, rank_tier?: number) =>
    request<import('./types').WinProbability>('/api/win-probability', {
      method: 'POST',
      body: JSON.stringify({ enemy_hero_ids, hero_id, role, rank_tier }),
    }),

  screenshot: async (file: File): Promise<ScreenshotResult> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/api/screenshot/analyse`, {
      method: 'POST',
      headers: { 'x-user-id': userId(), ...premiumHeaders() },
      body: form,
    });
    if (!res.ok) {
      let detail = `Upload failed (${res.status})`;
      try {
        detail = (await res.json()).detail || detail;
      } catch {
        /* ignore */
      }
      throw new ApiError(detail, res.status);
    }
    return res.json();
  },

  coach: (match_id: number, account_id?: number) =>
    request<{ coach_report: CoachReport; cached: boolean }>('/api/match/coach', {
      method: 'POST',
      body: JSON.stringify({ match_id, account_id }),
    }),
};
