'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertCircle, Loader2, Swords } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import type { Hero, Meta, PanicResult, Report } from '@/lib/types';
import { cn } from '@/lib/format';
import { Header, type TabKey } from '@/components/Header';
import { HeroGrid } from '@/components/HeroGrid';
import { DraftControls } from '@/components/DraftControls';
import { PanicView } from '@/components/PanicView';
import { ReportView } from '@/components/ReportView';
import { HeroPortrait } from '@/components/HeroPortrait';
import { ScreenshotPanel } from '@/components/panels/ScreenshotPanel';
import { CoachPanel } from '@/components/panels/CoachPanel';
import { MetaPanel } from '@/components/panels/MetaPanel';
import { UsageBar } from '@/components/panels/UsageBar';

export default function Home() {
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [role, setRole] = useState('carry');
  const [rank, setRank] = useState(55);
  const [tab, setTab] = useState<TabKey>('lastpick');
  const [premium, setPremium] = useState(false);

  const [panic, setPanic] = useState<PanicResult | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState<'panic' | 'report' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  useEffect(() => {
    api.heroes().then(setHeroes).catch((e) => setError(String(e.message ?? e)));
    api.meta().then(setMeta).catch(() => undefined);
    setPremium(window.localStorage.getItem('draftmaster_premium') === '1');
  }, []);

  const togglePremium = () => {
    const next = !premium;
    setPremium(next);
    window.localStorage.setItem('draftmaster_premium', next ? '1' : '0');
  };

  const toggleHero = useCallback(
    (id: number) => {
      setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= 5 ? prev : [...prev, id]));
      setPanic(null);
      setReport(null);
      setError(null);
    },
    [],
  );

  const clear = () => {
    setSelected([]);
    setPanic(null);
    setReport(null);
    setError(null);
    setElapsed(null);
  };

  const run = async (kind: 'panic' | 'report') => {
    if (selected.length === 0) {
      setError('Select at least one enemy hero.');
      return;
    }
    setError(null);
    setLoading(kind);
    const t0 = performance.now();
    try {
      if (kind === 'panic') {
        const res = await api.panic(selected, role, rank);
        setPanic(res);
        setTab('lastpick');
      } else {
        const res = await api.analyse(selected, undefined, role, rank);
        setReport(res.report);
        setTab('draft');
      }
      setElapsed(Math.round(performance.now() - t0));
    } catch (e) {
      const err = e as ApiError;
      setError(err.message ?? 'Something went wrong.');
    } finally {
      setLoading(null);
    }
  };

  const selectedHeroes = useMemo(
    () => selected.map((id) => heroes.find((h) => h.id === id)).filter(Boolean) as Hero[],
    [selected, heroes],
  );

  return (
    <div className="min-h-dvh">
      <Header tab={tab} onTab={setTab} patch={meta?.patch} premium={premium} onPremium={togglePremium} />

      <main className="mx-auto flex max-w-6xl flex-col gap-4 px-3 py-4 sm:px-5 sm:py-6">
        {/* Hero: value prop + instant action */}
        <section className="card card-pad">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-xl">
              <h1 className="text-2xl font-black leading-tight text-white sm:text-3xl">
                Your enemy draft is already decided.
                <span className="block text-radiant">Now win the game.</span>
              </h1>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                DraftMaster AI turns the enemy lineup into one actionable plan: the best hero, the exact
                build, the items to avoid, kill priority, power spikes and win conditions — computed from{' '}
                <span className="text-slate-200">{heroes.length || 127} heroes</span> of real OpenDota match
                data, not a static guide.
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => run('panic')}
                  disabled={loading !== null || selected.length === 0}
                  className="btn-danger"
                >
                  {loading === 'panic' ? <Loader2 className="h-4 w-4 animate-spin" /> : <span>🚨</span>}
                  I&apos;M LAST PICK
                </button>
                <button
                  type="button"
                  onClick={() => run('report')}
                  disabled={loading !== null || selected.length === 0}
                  className="btn-primary"
                >
                  {loading === 'report' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Swords className="h-4 w-4" />}
                  One Click Win Plan™
                </button>
                {selected.length > 0 && (
                  <button type="button" onClick={clear} className="btn-ghost">
                    Clear
                  </button>
                )}
                {elapsed !== null && (
                  <span className="chip border-radiant/40 text-radiant">answered in {elapsed} ms</span>
                )}
              </div>
            </div>

            <div className="flex w-full max-w-xs flex-col gap-2 rounded-xl border border-base-700 bg-base-900/60 p-3">
              <p className="label">Enemy draft</p>
              <div className="flex gap-2">
                {Array.from({ length: 5 }).map((_, i) => {
                  const h = selectedHeroes[i];
                  return h ? (
                    <HeroPortrait key={h.id} icon={h.icon} name={h.localized_name} size={40} />
                  ) : (
                    <span
                      key={i}
                      className="flex h-10 w-10 items-center justify-center rounded-md border border-dashed border-base-600 text-xs text-slate-600"
                    >
                      {i + 1}
                    </span>
                  );
                })}
              </div>
              <DraftControls role={role} onRole={setRole} rank={rank} onRank={setRank} compact />
              <UsageBar premium={premium} usage={panic?.usage ?? undefined} />
            </div>
          </div>
        </section>

        {/* Draft input + result */}
        {(tab === 'lastpick' || tab === 'draft') && (
          <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
            <section className="card card-pad">
              <h2 className="section-title mb-3">Enemy draft input</h2>
              <HeroGrid heroes={heroes} selected={selected} onToggle={toggleHero} max={5} />
            </section>

            <section className="flex flex-col gap-3">
              {error && (
                <div className="flex items-start gap-2 rounded-xl border border-dire/50 bg-dire/10 p-3 text-sm text-dire">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
              {loading && (
                <div className="card card-pad flex items-center gap-3 text-sm text-slate-300">
                  <Loader2 className="h-4 w-4 animate-spin text-radiant" />
                  Reading {selected.length} enemy heroes against the live meta…
                </div>
              )}
              {!loading && tab === 'lastpick' && panic && <PanicView result={panic} onFullReport={() => run('report')} />}
              {!loading && tab === 'draft' && report && <ReportView report={report} />}
              {!loading && !panic && !report && (
                <EmptyState onScreenshot={() => setTab('screenshot')} />
              )}
            </section>
          </div>
        )}

        {tab === 'screenshot' && <ScreenshotPanel />}
        {tab === 'coach' && <CoachPanel premium={premium} onPremium={togglePremium} />}
        {tab === 'meta' && <MetaPanel meta={meta} />}
      </main>

      <footer className="border-t border-base-800 py-6 text-center text-[11px] text-slate-600">
        DraftMaster AI · data © OpenDota / Valve · not affiliated with Valve Corporation ·{' '}
        {premium ? 'Premium' : 'Free'} plan
      </footer>
    </div>
  );
}

function EmptyState({ onScreenshot }: { onScreenshot: () => void }) {
  return (
    <div className="card card-pad flex flex-col items-center gap-3 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-base-800 text-2xl">🧠</span>
      <h3 className="text-lg font-bold text-white">Select the enemy draft</h3>
      <p className="max-w-md text-sm text-slate-400">
        Pick up to five enemy heroes, then hit <span className="text-dire">I&apos;M LAST PICK</span> for a
        one-screen win plan or <span className="text-radiant">One Click Win Plan</span> for the full
        11-section report.
      </p>
      <button type="button" onClick={onScreenshot} className={cn('btn-ghost mt-1')}>
        …or upload a draft screenshot
      </button>
    </div>
  );
}
