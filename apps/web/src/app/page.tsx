'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Loader2, Swords } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { api, ApiError, getSessionToken, isNetworkError } from '@/lib/api';
import { installAnalytics, track } from '@/lib/analytics';
import type { Hero, Meta, PanicResult, Report, Usage } from '@/lib/types';
import { cn } from '@/lib/format';
import { Header, type TabKey } from '@/components/Header';
import { HeroGrid } from '@/components/HeroGrid';
import { DraftControls } from '@/components/DraftControls';
import { PanicView } from '@/components/PanicView';
import { ReportView } from '@/components/ReportView';
import { HeroPortrait } from '@/components/HeroPortrait';
import { ReportSkeleton } from '@/components/ReportSkeleton';
import { PremiumModal } from '@/components/PremiumModal';
import { ShareBar } from '@/components/ShareBar';
import { HeroStrategyView } from '@/components/HeroStrategyView';
import { ModeChooser } from '@/components/ModeChooser';
import { ScreenshotPanel } from '@/components/panels/ScreenshotPanel';
import { CoachPanel } from '@/components/panels/CoachPanel';
import { MetaPanel } from '@/components/panels/MetaPanel';
import { UsageBar } from '@/components/panels/UsageBar';

type RunError = { message: string; quota: boolean };

export default function Home() {
  const t = useTranslations();
  const locale = useLocale();
  const [heroes, setHeroes] = useState<Hero[]>([]);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [role, setRole] = useState('carry');
  const [rank, setRank] = useState(55);
  const [tab, setTab] = useState<TabKey>('lastpick');
  const [premium, setPremium] = useState(false);
  const [showPlans, setShowPlans] = useState(false);
  const [showModes, setShowModes] = useState(false);

  // Deep link from the public pages: /?upgrade=1 opens the plan panel, so the
  // checkout link on /panic lands straight on the purchase decision.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    if (params.get('upgrade') === '1') {
      setShowPlans(true);
      track('upgrade_clicked', { source: 'deep_link' });
    }
  }, []);

  const [panic, setPanic] = useState<PanicResult | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  // Single source of truth for the header quota bar: every paid action (panic,
  // full report, screenshot) reports the usage it consumed, so the count stays
  // correct no matter which feature the user touched.
  const [usage, setUsage] = useState<Usage | undefined>(undefined);
  const [loading, setLoading] = useState<'panic' | 'report' | null>(null);
  const [error, setError] = useState<RunError | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);
  const [lastRun, setLastRun] = useState<'panic' | 'report' | null>(null);
  // Remembers the last analysis so a language switch can refresh the same draft
  // in the new locale (the backend does not charge quota for a repeat request).
  const lastRunRef = useRef<{ kind: 'panic' | 'report'; heroIds: number[]; role: string; rank: number } | null>(null);
  const localeRef = useRef(locale);

  useEffect(() => {
    installAnalytics();
    track('page_view', { locale });
    api.heroes()
      .then(setHeroes)
      .catch((e) => setError(describeError(e, t)));
    api.meta().then(setMeta).catch(() => undefined);
    // Premium is proved by a signed session token, verified server-side on
    // every paid request. The token is only a cache of that proof — it cannot
    // be forged into entitlement.
    setPremium(Boolean(getSessionToken()));
  }, [t]);

  useEffect(() => {
    if (localeRef.current === locale) return;
    localeRef.current = locale;
    const prev = lastRunRef.current;
    if (!prev) return;
    setLoading(prev.kind);
    setError(null);
    (async () => {
      try {
        if (prev.kind === 'panic') {
          const res = await api.panic(prev.heroIds, prev.role, prev.rank);
          setPanic(res);
          setUsage(res.usage);
        } else {
          const res = await api.analyse(prev.heroIds, undefined, prev.role, prev.rank);
          setReport(res.report);
          setUsage(res.usage);
        }
      } catch (e) {
        setError(describeError(e, t));
      } finally {
        setLoading(null);
      }
    })();
  }, [locale, t]);

  const refreshPremium = useCallback(() => {
    // Re-verify with the server; the token alone is not proof of entitlement.
    api.billingSession()
      .then((s) => setPremium(s.plan === 'premium'))
      .catch(() => setPremium(Boolean(getSessionToken())));
  }, []);

  const toggleHero = useCallback(
    (id: number) => {
      setSelected((prev) => {
        const next = prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= 5 ? prev : [...prev, id];
        track('draft_started', { count: next.length });
        return next;
      });
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
    setLastRun(null);
  };

  const run = async (kind: 'panic' | 'report') => {
    if (selected.length === 0) {
      setError({ message: t('errors.selectAtLeastOne'), quota: false });
      return;
    }
    setError(null);
    setLoading(kind);
    setLastRun(kind);
    lastRunRef.current = { kind, heroIds: selected, role, rank };
    const t0 = performance.now();
    try {
      if (kind === 'panic') {
        const res = await api.panic(selected, role, rank);
        setPanic(res);
        setUsage(res.usage);
        setTab('lastpick');
        track('panic_run', { heroes: selected.length, ms: Math.round(performance.now() - t0) });
      } else {
        const res = await api.analyse(selected, undefined, role, rank);
        setReport(res.report);
        setUsage(res.usage);
        setTab('draft');
        track('analysis_run', { heroes: selected.length, ms: Math.round(performance.now() - t0) });
      }
      setElapsed(Math.round(performance.now() - t0));
    } catch (e) {
      const info = describeError(e, t);
      setError(info);
      if (e instanceof ApiError && e.status === 402) {
        // The paywall moment: highest purchase intent in the whole funnel.
        track('paywall_hit', { feature: kind });
      }
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
      <Header tab={tab} onTab={setTab} patch={meta?.patch} premium={premium} onPremium={() => setShowPlans(true)} />

      <main className="mx-auto flex w-full max-w-[1600px] flex-col gap-4 px-3 py-4 sm:px-6 sm:py-6">
        {/* Hero: value prop + instant action */}
        <section className="card card-pad">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="max-w-xl">
              <h1 className="text-2xl font-black leading-tight text-white sm:text-3xl xl:text-4xl">
                {t('hero.headline1')}
                <span className="block text-radiant">{t('hero.headline2')}</span>
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400 xl:text-base">
                {t('hero.sub1')}{' '}
                <span className="text-slate-200">{t('hero.sub2', { count: heroes.length || 127 })}</span>{' '}
                {t('hero.sub3')}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => run('panic')}
                  disabled={loading !== null || selected.length === 0}
                  className="btn-danger"
                >
                  {loading === 'panic' ? <Loader2 className="h-4 w-4 animate-spin" /> : <span>🚨</span>}
                  {t('hero.panic')}
                </button>
                <button
                  type="button"
                  onClick={() => run('report')}
                  disabled={loading !== null || selected.length === 0}
                  className="btn-primary"
                >
                  {loading === 'report' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Swords className="h-4 w-4" />}
                  {t('hero.oneClick')}
                </button>
                <button type="button" onClick={() => setTab('mystrategy')} className="btn-ghost">
                  🛡️ {t('tabs.mystrategy')}
                </button>
                {selected.length > 0 && (
                  <button type="button" onClick={clear} className="btn-ghost">
                    {t('hero.clear')}
                  </button>
                )}
                {elapsed !== null && (
                  <span className="chip border-radiant/40 text-radiant">{t('hero.answeredIn', { ms: elapsed })}</span>
                )}
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {t('hero.notPickedYet')}{' '}
                <button
                  type="button"
                  onClick={() => setShowModes(true)}
                  className="font-semibold text-radiant underline underline-offset-2"
                >
                  {t('hero.compareModes')}
                </button>
              </p>
            </div>

            <div className="flex w-full max-w-xs flex-col gap-2 rounded-xl border border-base-700 bg-base-900/60 p-3">
              <p className="label">{t('hero.enemyDraft')}</p>
              <div className="flex gap-2">
                {Array.from({ length: 5 }).map((_, i) => {
                  const h = selectedHeroes[i];
                  return h ? (
                    <HeroPortrait key={`hero-${h.id}`} icon={h.icon} name={h.localized_name} size={40} />
                  ) : (
                    <span
                      key={`slot-${i}`}
                      className="flex h-10 w-10 items-center justify-center rounded-md border border-dashed border-base-600 text-xs text-slate-600"
                    >
                      {i + 1}
                    </span>
                  );
                })}
              </div>
              <DraftControls role={role} onRole={setRole} rank={rank} onRank={setRank} compact />
              <UsageBar premium={premium} usage={usage} />
            </div>
          </div>
        </section>

        {/* Draft input + result */}
        {(tab === 'lastpick' || tab === 'draft') && (
          <div className="grid gap-4 lg:grid-cols-[360px_1fr] xl:grid-cols-[420px_1fr]">
            <section className="card card-pad">
              <h2 className="section-title mb-3">{t('draft.input')}</h2>
              <HeroGrid heroes={heroes} selected={selected} onToggle={toggleHero} max={5} />
            </section>

            <section className="flex flex-col gap-3">
              {error && (
                <div
                  className={cn(
                    'flex items-start gap-2 rounded-xl border p-3 text-sm',
                    error.quota ? 'border-gold/50 bg-gold/10 text-gold' : 'border-dire/50 bg-dire/10 text-dire',
                  )}
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div className="flex flex-1 flex-col gap-1.5">
                    {error.quota && <span className="font-semibold">{t('errors.quotaTitle')}</span>}
                    <span>{error.message}</span>
                    {error.quota && (
                      // The paywall moment has the highest purchase intent in
                      // the whole product; never dead-end it with a message.
                      <button
                        type="button"
                        onClick={() => {
                          track('upgrade_clicked', { source: 'paywall_banner' });
                          setShowPlans(true);
                        }}
                        className="btn-primary mt-0.5 self-start"
                      >
                        {t('errors.unlock')}
                      </button>
                    )}
                    {!error.quota && lastRun && selected.length > 0 && (
                      <button
                        type="button"
                        onClick={() => run(lastRun)}
                        className="self-start text-xs font-semibold underline underline-offset-2"
                      >
                        {t('errors.retry')}
                      </button>
                    )}
                  </div>
                </div>
              )}
              {loading && <ReportSkeleton label={t('loading.reading', { count: selected.length })} />}
              {!loading && tab === 'lastpick' && panic && (
                <>
                  <PanicView result={panic} onFullReport={() => run('report')} />
                  <div className="flex flex-wrap items-center gap-2">
                    <ShareBar
                      enemyIds={selected}
                      role={role}
                      rank={rank}
                      onQuota={() => setShowPlans(true)}
                    />
                    <span className="text-xs text-slate-500">{t('share.subhint')}</span>
                  </div>
                </>
              )}
              {!loading && tab === 'draft' && report && <ReportView report={report} />}
              {!loading && !panic && !report && (
                <EmptyState onScreenshot={() => setTab('screenshot')} />
              )}
            </section>
          </div>
        )}

        {tab === 'mystrategy' && (
          <HeroStrategyView
            heroes={heroes}
            role={role}
            rank={rank}
            premium={premium}
            onUsage={setUsage}
            onUpgrade={() => setShowPlans(true)}
          />
        )}
        {tab === 'screenshot' && <ScreenshotPanel onUsage={setUsage} />}
        {tab === 'coach' && <CoachPanel premium={premium} onPremium={() => setShowPlans(true)} />}
        {tab === 'meta' && <MetaPanel meta={meta} />}
      </main>

      <ModeChooser
        open={showModes}
        onClose={() => setShowModes(false)}
        onPick={(mode) => {
          setShowModes(false);
          setTab(mode);
          track('mode_selected', { mode });
        }}
      />

      <PremiumModal
        open={showPlans}
        premium={premium}
        onClose={() => setShowPlans(false)}
        onActivated={refreshPremium}
      />

      <footer className="border-t border-base-800 py-6 text-center text-[11px] text-slate-600">
        {t('footer.disclaimer')}{' '}
        <a
          href="https://www.opendota.com"
          target="_blank"
          rel="noreferrer noopener"
          className="underline underline-offset-2 hover:text-slate-400"
        >
          {t('footer.data')}
        </a>
        {' · '}
        {t('footer.plan', { tier: premium ? t('footer.premium') : t('footer.free') })}
      </footer>
    </div>
  );
}

function describeError(e: unknown, t: (key: string) => string): RunError {
  const err = e as ApiError;
  if (isNetworkError(err)) return { message: t('errors.network'), quota: false };
  if (err?.status === 402) return { message: err.message || t('errors.generic'), quota: true };
  return { message: err?.message || t('errors.generic'), quota: false };
}

function EmptyState({ onScreenshot }: { onScreenshot: () => void }) {
  const t = useTranslations('empty');
  const tHero = useTranslations('hero');
  return (
    <div className="card card-pad flex flex-col items-center gap-3 py-12 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-base-800 text-2xl">🧠</span>
      <h3 className="text-lg font-bold text-white">{t('title')}</h3>
      <p className="max-w-md text-sm text-slate-400">
        {t('body1')} <span className="text-dire">{tHero('panic')}</span> {t('body2')}{' '}
        <span className="text-radiant">{tHero('oneClick')}</span> {t('body3')}
      </p>
      <button type="button" onClick={onScreenshot} className={cn('btn-ghost mt-1')}>
        {t('screenshot')}
      </button>
    </div>
  );
}
