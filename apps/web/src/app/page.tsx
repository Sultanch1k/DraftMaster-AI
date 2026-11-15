'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle } from 'lucide-react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { api, ApiError, getSessionToken, isNetworkError } from '@/lib/api';
import { installAnalytics, track } from '@/lib/analytics';
import type { Hero, Meta, PanicResult, Report, Usage } from '@/lib/types';
import { cn } from '@/lib/format';
import { Header, type TabKey } from '@/components/Header';
import { HeroGrid } from '@/components/HeroGrid';
import { DraftControls } from '@/components/DraftControls';
import { PanicWinPlan } from '@/components/winplan/PanicWinPlan';
import { ReportView } from '@/components/ReportView';
import { ReportSkeleton } from '@/components/ReportSkeleton';
import { PremiumModal } from '@/components/PremiumModal';
import { HeroStrategyView } from '@/components/HeroStrategyView';
import { ScreenshotPanel } from '@/components/panels/ScreenshotPanel';
import { CoachPanel } from '@/components/panels/CoachPanel';
import { MetaPanel } from '@/components/panels/MetaPanel';
import { UsageBar } from '@/components/panels/UsageBar';
import { HomeHero } from '@/components/home/HomeHero';
import { ActionBar } from '@/components/home/ActionBar';
import { HowItWorks } from '@/components/home/HowItWorks';

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
        {/* Cinematic opening: value prop + the two first-class modes */}
        <HomeHero
          mode={tab === 'mystrategy' ? 'strategy' : 'counter'}
          onCounter={() => setTab('lastpick')}
          onStrategy={() => setTab('mystrategy')}
          patch={meta?.patch}
          heroCount={heroes.length}
        />

        {/* Personalisation + plan status, always visible once a draft exists */}
        <section className="card card-pad">
          <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
            <DraftControls role={role} onRole={setRole} rank={rank} onRank={setRank} />
            <div className="w-full lg:max-w-xs">
              <UsageBar premium={premium} usage={usage} />
            </div>
          </div>
        </section>

        {/* Draft input + result */}
        {(tab === 'lastpick' || tab === 'draft') && (
          <div className="grid gap-4 lg:grid-cols-[360px_1fr] xl:grid-cols-[420px_1fr]">
            <div className="flex flex-col gap-4">
              <section className="card card-pad">
                <h2 className="section-title mb-3">{t('draft.input')}</h2>
                <HeroGrid heroes={heroes} selected={selected} onToggle={toggleHero} max={5} />
              </section>
              <ActionBar
                heroes={selectedHeroes}
                loading={loading}
                elapsed={elapsed}
                onPanic={() => run('panic')}
                onReport={() => run('report')}
                onClear={clear}
              />
            </div>

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
                <PanicWinPlan
                  result={panic}
                  enemyIds={selected}
                  role={role}
                  rank={rank}
                  onFullReport={() => run('report')}
                  onQuota={() => setShowPlans(true)}
                />
              )}
              {!loading && tab === 'draft' && report && <ReportView report={report} />}
              {!loading && !panic && !report && (
                <EmptyState onScreenshot={() => setTab('screenshot')} />
              )}
            </section>
          </div>
        )}

        {/* Editorial framing, shown while the user has not produced a plan yet */}
        {!panic && !report && tab !== 'mystrategy' && <HowItWorks />}

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

      <PremiumModal
        open={showPlans}
        premium={premium}
        onClose={() => setShowPlans(false)}
        onActivated={refreshPremium}
      />

      <footer className="border-t border-base-800 py-6 text-center text-[11px] text-ink-faint">
        {t('footer.disclaimer')}{' '}
        <a
          href="https://www.opendota.com"
          target="_blank"
          rel="noreferrer noopener"
          className="underline underline-offset-2 hover:text-ink-muted"
        >
          {t('footer.data')}
        </a>
        {' · '}
        {t('footer.plan', { tier: premium ? t('footer.premium') : t('footer.free') })}
        {' · '}
        <Link href="/blog" className="underline underline-offset-2 hover:text-ink-muted">
          {t('footer.blog')}
        </Link>
        {' · '}
        <Link href="/privacy" className="underline underline-offset-2 hover:text-ink-muted">
          {t('footer.privacy')}
        </Link>
        {' · '}
        <Link href="/terms" className="underline underline-offset-2 hover:text-ink-muted">
          {t('footer.terms')}
        </Link>
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
      <h3 className="text-lg font-bold text-ink">{t('title')}</h3>
      <p className="max-w-md text-sm text-ink-muted">
        {t('body1')} <span className="text-dire">{tHero('panic')}</span> {t('body2')}{' '}
        <span className="text-radiant">{tHero('oneClick')}</span> {t('body3')}
      </p>
      <button type="button" onClick={onScreenshot} className={cn('btn-ghost mt-1')}>
        {t('screenshot')}
      </button>
    </div>
  );
}
