/**
 * First-party funnel analytics.
 *
 * Events are batched and flushed to /api/events so we can see where users drop
 * off between landing and paying. Deliberately tiny: no external script, no
 * cookie, nothing to block, and it never throws into the UI.
 */
type Props = Record<string, string | number | boolean | null | undefined>;

const queue: { name: string; props: Props; ts: number }[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function userId(): string {
  if (typeof window === 'undefined') return 'server';
  return window.localStorage.getItem('draftmaster_user') || 'anonymous';
}

async function flush(): Promise<void> {
  if (queue.length === 0) return;
  const batch = queue.splice(0, queue.length);
  try {
    await fetch('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        events: batch.map((e) => ({ name: e.name, user_id: userId(), props: e.props })),
      }),
      keepalive: true,
    });
  } catch {
    /* analytics must never break the product */
  }
}

export function track(name: string, props: Props = {}): void {
  if (typeof window === 'undefined') return;
  queue.push({ name, props, ts: Date.now() });
  if (timer) clearTimeout(timer);
  timer = setTimeout(flush, 1200);
  if (queue.length >= 10) void flush();
}

/** Fire-and-forget flush on page hide so the last events are not lost. */
export function installAnalytics(): void {
  if (typeof window === 'undefined') return;
  window.addEventListener('pagehide', () => void flush());
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') void flush();
  });
}
