'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Loader2, Zap } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError } from '@/lib/api';
import { installAnalytics, track } from '@/lib/analytics';
import type { Hero, PanicResult } from '@/lib/types';
import { HeroGrid } from './HeroGrid';
import { DraftControls } from './DraftControls';
import { PanicView } from './PanicView';
import { ShareBar } from './ShareBar';

/**
 * Public "I'M LAST PICK" tool — the acquisition surface for the flagship flow.
 *
 * A visitor lands, taps the enemy draft, and gets a full plan without ever
 * seeing the app shell or creating an account. The daily free limit applies as
 * it does everywhere else, so this is a real funnel entry point, not a demo.
 */
export function PanicLanding() {
  const t = useTranslations('panicLanding');
  const tShare = useTranslations('share');
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [selected, setSelected] = useState<number[]>([]);
  const [role, setRole] = useState('carry');
  const [rank, setRank] = useState(55);
  const [result, setResult] = useState<PanicResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<{ message: string; quota: boolean } | null>(null);

  useEffect(() => {
    installAnalytics();
    track('page_view', { source: 'panic_landing' });
    api.heroes().then(setHeroes).catch(() => undefined);
  }, []);

  const toggle = (id: number) => {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= 5 ? prev : [...prev, id]));
    setResult(null);
    setError(null);
  };

  const run = async () => {
    if (selected.length === 0) {
      setError({ message: t('needOne'), quota: false });
      return;
    }
    setLoading(true);
    setError(null);
    const t0 = performance.now();
    try {
      const res = await api.panic(selected, role, rank);
      setResult(res);
      track('panic_run', { heroes: selected.length, ms: Math.round(performance.now() - t0), source: 'panic_landing' });
    } catch (e) {
      if (e instanceof ApiError && e.status === 402) {
        setError({ message: t('quota'), quota: true });
        track('paywall_hit', { feature: 'panic_landing' });
      } else {
        setError({ message: t('failed'), quota: false });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[360px_1fr] xl:grid-cols-[420px_1fr]">
      <section className="card card-pad">
        <h2 className="section-title mb-3">{t('enemyDraft')}</h2>
        <HeroGrid heroes={heroes} selected={selected} onToggle={toggle} max={5} />
        <div className="mt-3">
          <DraftControls role={role} onRole={setRole} rank={rank} onRank={setRank} compact />
        </div>
        <button type="button" onClick={run} disabled={loading} className="btn-danger mt-3 w-full justify-center">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {t('cta')}
        </button>
      </section>

      <section className="flex flex-col gap-3">
        {error && (
          <div className={`rounded-xl border p-3 text-sm ${error.quota ? 'border-gold/50 bg-gold/10 text-gold' : 'border-dire/50 bg-dire/10 text-dire'}`}>
            <p>{error.message}</p>
            {error.quota && (
              <Link
                href="/?upgrade=1"
                className="mt-1 inline-block text-xs font-semibold underline underline-offset-2"
                onClick={() => track('upgrade_clicked', { source: 'panic_landing' })}
              >
                {t('upgrade')}
              </Link>
            )}
          </div>
        )}
        {loading && (
          <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin text-radiant" />
            {t('loading')}
          </div>
        )}
        {!loading && result && (
          <>
            <PanicView result={result} />
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs text-slate-500">{tShare('subhint')}</span>
            </div>
          </>
        )}
        {!loading && !result && !error && <p className="card card-pad text-sm text-slate-400">{t('empty')}</p>}
      </section>
    </div>
  );
}
