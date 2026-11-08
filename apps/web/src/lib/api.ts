import type {
  BillingConfig,
  BillingSession,
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
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** True when the failure was a network/transport error rather than an HTTP response. */
export function isNetworkError(e: unknown): boolean {
  return e instanceof ApiError && e.status === 0;
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

/** The signed premium session token, stored after a successful activation. */
export function getSessionToken(): string {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem('draftmaster_session') || '';
}

export function setSessionToken(token: string): void {
  if (typeof window === 'undefined') return;
  if (token) window.localStorage.setItem('draftmaster_session', token);
  else window.localStorage.removeItem('draftmaster_session');
}

function premiumHeaders(): Record<string, string> {
  const token = getSessionToken();
  return token ? { authorization: `Bearer ${token}` } : {};
}

/**
 * The active locale lives in a cookie so server and client agree on one value.
 * Sending it explicitly lets the API return prose in the right language.
 */
export function currentLocale(): string {
  if (typeof document === 'undefined') return 'en';
  const match = document.cookie.match(/(?:^|;\s*)draftmaster_locale=([^;]+)/);
  return match?.[1] === 'ru' ? 'ru' : 'en';
}

function localeHeader(): Record<string, string> {
  return { 'x-locale': currentLocale() };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'x-user-id': userId(),
        ...premiumHeaders(),
        ...localeHeader(),
        ...(init?.headers || {}),
      },
    });
  } catch {
    // fetch only rejects on transport failure — surface it as a typed error so
    // the UI can show a connection message instead of a raw exception.
    throw new ApiError('Network request failed', 0, 'network');
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    let code: string | undefined;
    try {
      const body = await res.json();
      detail = extractDetail(body.detail) || detail;
      code = body.code;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status, code);
  }
  return res.json() as Promise<T>;
}

/**
 * FastAPI returns a string for handled errors but a list of validation objects
 * for 422s. Normalise both to a single readable line so the UI never renders
 * "[object Object]" or a raw schema dump.
 */
function extractDetail(detail: unknown): string | null {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const first = detail[0];
    if (first && typeof first === 'object' && 'msg' in first) {
      return String((first as { msg: unknown }).msg);
    }
    return null;
  }
  return null;
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
    let res: Response;
    try {
      res = await fetch(`${BASE}/api/screenshot/analyse`, {
        method: 'POST',
        headers: { 'x-user-id': userId(), ...premiumHeaders(), ...localeHeader() },
        body: form,
      });
    } catch {
      throw new ApiError('Network request failed', 0, 'network');
    }
    if (!res.ok) {
      let detail = `Upload failed (${res.status})`;
      try {
        detail = extractDetail((await res.json()).detail) || detail;
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

  billingConfig: () => request<BillingConfig>('/api/billing/config'),

  billingSession: () => request<BillingSession>('/api/billing/session'),

  activate: (license_key: string) =>
    request<BillingSession>('/api/billing/activate', {
      method: 'POST',
      body: JSON.stringify({ license_key }),
    }),

  subscribeEmail: (email: string) =>
    request<{ ok: boolean }>('/api/subscribe', {
      method: 'POST',
      body: JSON.stringify({ email, user_id: userId() }),
    }),
};
