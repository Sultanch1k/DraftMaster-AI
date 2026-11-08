'use client';

import { useCallback, useMemo, useState } from 'react';
import {
  AlertTriangle,
  Ban,
  Clock,
  Flame,
  Layers,
  Loader2,
  Shield,
  ShieldAlert,
  Sparkles,
  Swords,
  Target,
  X,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { api, ApiError, isNetworkError } from '@/lib/api';
import { track } from '@/lib/analytics';
import type { Hero, HeroStrategy, ItemPick, Usage } from '@/lib/types';
import { cn, scoreColor } from '@/lib/format';
import { Card } from './Card';
import { HeroPicker } from './HeroPicker';
import { HeroPortrait } from './HeroPortrait';
import { ItemBuildCard, OneSentencePlan, PowerSpikeCard, TargetPriorityCard, WinConditionsCard } from './ReportCards';
import { WinProbabilityBar, WinProbFactors } from './WinProbability';
import { ReportSkeleton } from './ReportSkeleton';

type Props = {
  heroes: Hero[];
  role: string;
  rank: number;
  premium: boolean;
  onUsage: (u: Usage) => void;
  onUpgrade: () => void;
};

/**
 * My Hero Strategy — the "I already picked my hero" mode.
 *
 * The user fixes their hero and five enemies, then gets a matchup-specific game
 * plan. This view is intentionally a sibling of the counter-pick flow: same
 * design language, same interaction patterns, different question.
 */
export function HeroStrategyView({ heroes, role, rank, premium, onUsage, onUpgrade }: Props) {
  const t = useTranslations('mystrategy');
  const tHero = useTranslations('hero');
  const [myHero, setMyHero] = useState<number | null>(null);
  const [enemies, setEnemies] = useState<number[]>([]);
  const [strategy, setStrategy] = useState<HeroStrategy | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  const heroById = useMemo(() => new Map(heroes.map((h) => [h.id, h])), [heroes]);
  const enemyHeroes = useMemo(
    () => enemies.map((id) => heroById.get(id)).filter(Boolean) as Hero[],
    [enemies, heroById],
  );
  const pickedHero = myHero ? heroById.get(myHero) : undefined;

  const toggleEnemy = useCallback((id: number) => {
    setStrategy(null);
    setError(null);
    setMyHero((prev) => (prev === id ? null : prev));
    setEnemies((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : prev.length >= 5 ? prev : [...prev, id]));
  }, []);

  const selectHero = useCallback((id: number) => {
    setMyHero((prev) => (prev === id ? null : id));
    setEnemies((prev) => prev.filter((x) => x !== id));
    setStrategy(null);
    setError(null);
  }, []);

  const clearAll = () => {
    setMyHero(null);
    setEnemies([]);
    setStrategy(null);
    setError(null);
    setElapsed(null);
  };

  const canRun = myHero !== null && enemies.length === 5;

  const run = async () => {
    if (myHero === null) {
      setError(t('needHero'));
      return;
    }
    if (enemies.length !== 5) {
      setError(t('needFive', { count: enemies.length }));
      return;
    }
    setError(null);
    setLoading(true);
    setStrategy(null);
    const t0 = performance.now();
    try {
      const res = await api.heroStrategy(myHero, enemies, role, rank);
      setStrategy(res.strategy);
      onUsage(res.usage);
      setElapsed(Math.round(performance.now() - t0));
      track('hero_strategy_run', { hero_id: myHero, enemies: enemies.length, ms: Math.round(performance.now() - t0) });
    } catch (e) {
      if (isNetworkError(e)) {
        setError(tHero('enemyDraft') && 'Network request failed');
      } else if (e instanceof ApiError && e.status === 402) {
        track('paywall_hit', { feature: 'hero_strategy' });
        setError(e.message);
      } else {
        setError((e as ApiError).message || 'Request failed');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* --- input ------------------------------------------------------- */}
      <Card>
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-black text-white sm:text-xl">{t('title')}</h2>
          <p className="text-sm text-slate-400">{t('subtitle')}</p>
        </div>

        <div className="mt-4 flex flex-col gap-4">
          <div>
            <p className="label mb-1.5">{t('pickYourHero')}</p>
            <div className="mb-3 flex items-center gap-3">
              {pickedHero ? (
                <div className="flex items-center gap-2 rounded-lg border border-radiant/50 bg-radiant/10 px-3 py-2">
                  <HeroPortrait icon={pickedHero.icon} name={pickedHero.localized_name} size={40} priority />
                  <div>
                    <p className="text-sm font-bold text-white">{pickedHero.localized_name}</p>
                    <p className="text-[11px] text-slate-400">{pickedHero.roles.join(' · ')}</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => selectHero(pickedHero.id)}
                    className="ml-1 rounded p-1 text-slate-400 hover:text-white"
                    aria-label={t('changeHero')}
                    title={t('changeHero')}
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <span className="text-xs text-slate-500">{t('pickYourHeroHint')}</span>
              )}
            </div>
            <HeroPicker
              heroes={heroes}
              selected={myHero ? [myHero] : []}
              onToggle={selectHero}
              single
              disabledIds={enemies}
            />
          </div>

          <div>
            <p className="label mb-1.5">{t('enemyFive')}</p>
            <div className="mb-3 flex gap-1.5">
              {Array.from({ length: 5 }).map((_, i) => {
                const h = enemyHeroes[i];
                return h ? (
                  <button
                    key={`e-${h.id}`}
                    type="button"
                    onClick={() => toggleEnemy(h.id)}
                    title={h.localized_name}
                    className="group relative"
                  >
                    <HeroPortrait icon={h.icon} name={h.localized_name} size={44} />
                    <span className="absolute -right-1 -top-1 hidden h-4 w-4 items-center justify-center rounded-full bg-dire text-[9px] font-bold text-white group-hover:flex">
                      ✕
                    </span>
                  </button>
                ) : (
                  <span
                    key={`s-${i}`}
                    className="flex h-11 w-11 items-center justify-center rounded-md border border-dashed border-base-600 text-xs text-slate-600"
                  >
                    {i + 1}
                  </span>
                );
              })}
            </div>
            <p className={cn('mb-3 text-[11px]', enemies.length === 5 ? 'text-radiant' : 'text-slate-500')}>
              {t('enemyHint', { count: enemies.length })}
            </p>
            <HeroPicker heroes={heroes} selected={enemies} onToggle={toggleEnemy} disabledIds={myHero ? [myHero] : []} />
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <button type="button" onClick={run} disabled={loading || !canRun} className="btn-primary sm:w-auto">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Swords className="h-4 w-4" />}
              {t('analyze')}
            </button>
            {(myHero !== null || enemies.length > 0) && (
              <button type="button" onClick={clearAll} className="btn-ghost sm:w-auto">
                {tHero('clear')}
              </button>
            )}
            {elapsed !== null && strategy && (
              <span className="chip border-radiant/40 text-radiant">{tHero('answeredIn', { ms: elapsed })}</span>
            )}
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-dire/50 bg-dire/10 p-3 text-sm text-dire">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div className="flex flex-1 flex-col gap-1">
                <span>{error}</span>
                {error.toLowerCase().includes('free plan') || error.includes('Бесплатный') ? (
                  <button type="button" onClick={onUpgrade} className="self-start text-xs font-semibold underline underline-offset-2">
                    {premium ? '' : 'Upgrade to Premium'}
                  </button>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </Card>

      {loading && <ReportSkeleton label={t('loading')} />}
      {!loading && strategy && <StrategyReport strategy={strategy} />}
    </div>
  );
}

// ---------------------------------------------------------------------------

function StrategyReport({ strategy }: { strategy: HeroStrategy }) {
  const t = useTranslations('mystrategy');
  const ov = strategy.matchup_overview;
  const lane = strategy.lane_strategy;
  const tf = strategy.teamfight_strategy;

  return (
    <div className="flex flex-col gap-4">
      {/* Header: hero, difficulty, win probability */}
      <Card>
        <div className="grid gap-5 xl:grid-cols-[1fr_1.1fr]">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <HeroPortrait icon={strategy.hero.icon} name={strategy.hero.localized_name} size={64} priority />
              <div className="min-w-0">
                <p className="label">{t('title')}</p>
                <h2 className="text-2xl font-black leading-tight text-white">{strategy.hero.localized_name}</h2>
                <p className="text-xs text-slate-400">
                  {t('vs', { heroes: strategy.enemy_draft.map((h) => h.localized_name).join(', ') })}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className={cn('chip', ov.difficulty <= 2 ? 'border-radiant/50 text-radiant' : ov.difficulty === 3 ? 'border-gold/50 text-gold' : 'border-dire/50 text-dire')}>
                {t('difficulty')}: {t(diffKey(ov.difficulty))}
              </span>
              <span className="chip">{strategy.rank}</span>
              <span className="chip">{strategy.patch ? `patch ${strategy.patch}` : ''}</span>
            </div>

            <div className="rounded-lg border border-base-700 bg-base-900/50 p-3">
              <p className="label mb-1">{t('assessment')}</p>
              <p className="text-sm leading-relaxed text-slate-200">{ov.assessment}</p>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <Bullets title={t('advantages')} items={ov.advantages} tone="radiant" />
              <Bullets title={t('mistakes')} items={ov.biggest_mistakes} tone="dire" />
            </div>

            {(ov.favourable_matchups.length > 0 || ov.unfavourable_matchups.length > 0) && (
              <div className="flex flex-wrap gap-3 text-xs">
                {ov.favourable_matchups.length > 0 && (
                  <span className="text-slate-400">
                    <span className="font-semibold text-radiant">{t('favourable')}: </span>
                    {ov.favourable_matchups.join(', ')}
                  </span>
                )}
                {ov.unfavourable_matchups.length > 0 && (
                  <span className="text-slate-400">
                    <span className="font-semibold text-dire">{t('unfavourable')}: </span>
                    {ov.unfavourable_matchups.join(', ')}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4">
            <WinProbabilityBar wp={strategy.win_probability} />
            <WinProbFactors wp={strategy.win_probability} />
          </div>
        </div>
      </Card>

      <OneSentencePlan sentence={strategy.one_sentence_game_plan} label={t('s10')} />

      {/* 2 · Lane strategy */}
      <Card title={`2 · ${t('s2')}`} icon={<Clock className="h-4 w-4 text-gold" />}>
        <div className="grid gap-4 xl:grid-cols-2">
          <div className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip border-gold/40 text-gold">{t('laneRisk')}: {t(riskKey(lane.difficulty))}</span>
              <span className="chip">{lane.lane}</span>
            </div>
            <Bullets title={t('lanePlan')} items={lane.plan} tone="neutral" />
            {lane.likely_opponents.length > 0 && (
              <div>
                <p className="label mb-1.5">{t('likelyOpponents')}</p>
                <ul className="flex flex-col gap-2">
                  {lane.likely_opponents.map((o) => (
                    <li key={o.hero_id} className="rounded-lg border border-base-700 bg-base-850/60 p-2.5">
                      <div className="mb-1 flex items-center gap-2">
                        <HeroPortrait icon={null} name={o.name} size={24} />
                        <span className="text-sm font-semibold text-white">{o.name}</span>
                        <span
                          className={cn(
                            'ml-auto chip',
                            o.risk === 'high' ? 'border-dire/50 text-dire' : o.risk === 'medium' ? 'border-gold/50 text-gold' : 'border-radiant/50 text-radiant',
                          )}
                        >
                          {t('laneRisk')}: {t(riskKey(o.risk))}
                        </span>
                      </div>
                      <p className="text-[11px] leading-relaxed text-slate-300">{o.advice}</p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="flex flex-col gap-3">
            <Field label={t('trading')} value={lane.trading} />
            <Field label={t('aggression')} value={lane.aggression} />
            <Field label={t('survival')} value={lane.survival} />
            <Bullets title={t('callHelp')} items={lane.when_to_call_help} tone="gold" />
          </div>
        </div>
      </Card>

      {/* 3 · Skill build */}
      <Card title={`3 · ${t('s3')}`} icon={<Layers className="h-4 w-4 text-magic" />}>
        <SkillStrip strategy={strategy} />
        {strategy.skill_build.key_abilities.length > 0 && (
          <div className="mt-4">
            <p className="label mb-1.5">{t('keyAbilities')}</p>
            <ul className="flex flex-col gap-1.5">
              {strategy.skill_build.key_abilities.map((a) => (
                <li key={a.name} className="rounded-md border border-magic/30 bg-magic/5 px-2.5 py-1.5 text-[11px] text-slate-200">
                  <span className="font-semibold text-magic">{a.name}</span>
                  {a.dmg_type && a.dmg_type !== 'None' && <span className="ml-1.5 text-slate-500">({a.dmg_type})</span>} — {a.reason}
                </li>
              ))}
            </ul>
          </div>
        )}
        {strategy.skill_build.notes.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1.5">
            {strategy.skill_build.notes.map((n, i) => (
              <li key={i} className="rounded-md border border-base-700 bg-base-900/50 px-2.5 py-1.5 text-[11px] text-slate-300">
                {n}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* 4 · Item build */}
      <div>
        <SectionHeading n={4} title={t('s4')} />
        <ItemBuildCard build={strategy.item_build} />
      </div>

      {/* 5 · Enemy dossiers */}
      <div>
        <SectionHeading n={5} title={t('s5')} />
        <div className="flex flex-col gap-3">
          {strategy.enemy_dossiers.map((d) => (
            <DossierCard key={d.hero_id} dossier={d} />
          ))}
        </div>
      </div>

      {/* 6 · Teamfight */}
      <Card title={`6 · ${t('s6')}`} icon={<Shield className="h-4 w-4 text-dire" />}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <Field label={t('whereToStand')} value={tf.where_to_stand} />
          <Field label={t('targetFirst')} value={tf.target_first} />
          <Field label={t('avoid')} value={tf.avoid.join(', ') || '—'} tone="danger" />
          <Field label={t('whenToInitiate')} value={tf.when_to_initiate} />
          <Field label={t('whenToWait')} value={tf.when_to_wait} />
          <Field label={t('howToSurvive')} value={tf.how_to_survive} />
        </div>
        {tf.notes.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1.5">
            {tf.notes.map((n, i) => (
              <li key={i} className="rounded-md border border-base-700 bg-base-900/50 px-2.5 py-1.5 text-[11px] text-slate-300">
                {n}
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* 7 · Target priority + 8 · Power spikes */}
      <div className="grid gap-4 xl:grid-cols-2">
        <div>
          <SectionHeading n={7} title={t('s7')} />
          <TargetPriorityCard targets={strategy.target_priority} />
        </div>
        <div>
          <SectionHeading n={8} title={t('s8')} />
          <PowerSpikeCard spikes={strategy.power_spikes} />
        </div>
      </div>

      {/* 9 · Win conditions */}
      <div>
        <SectionHeading n={9} title={t('s9')} />
        <WinConditionsCard conditions={strategy.win_conditions} />
      </div>

      {/* Confidence disclosure */}
      <Card title={t('confidence')} icon={<ShieldAlert className="h-4 w-4 text-slate-400" />}>
        <div className="grid gap-3 sm:grid-cols-2">
          <Bullets title={t('measured')} items={strategy.data_confidence.measured} tone="radiant" />
          <Bullets title={t('inferred')} items={strategy.data_confidence.inferred} tone="gold" />
        </div>
        {strategy.data_confidence.notes.length > 0 && (
          <ul className="mt-3 flex flex-col gap-1.5">
            {strategy.data_confidence.notes.map((n, i) => (
              <li key={i} className="text-[11px] text-slate-400">• {n}</li>
            ))}
          </ul>
        )}
      </Card>

      <p className="pb-2 text-center text-[11px] text-slate-600">
        {t('generatedIn', { ms: strategy.generated_in_ms, patch: strategy.patch ?? '—' })}
      </p>
    </div>
  );
}

function DossierCard({ dossier: d }: { dossier: import('@/lib/types').EnemyDossier }) {
  const t = useTranslations('mystrategy');
  return (
    <Card
      title={d.name}
      icon={<HeroPortrait icon={d.icon} name={d.name} size={28} />}
      action={
        <span className={cn('chip', d.danger_score >= 60 ? 'border-dire/50 text-dire' : d.danger_score >= 40 ? 'border-gold/50 text-gold' : 'border-radiant/50 text-radiant')}>
          {t('dangerScore')} {d.danger_score.toFixed(0)}
        </span>
      }
    >
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="flex flex-col gap-3">
          <Bullets title={t('whatMakesDangerous')} items={d.what_makes_dangerous} tone="dire" />
          <Bullets title={t('howToAvoid')} items={d.how_to_avoid} tone="radiant" />
        </div>
        <div className="flex flex-col gap-3">
          {d.abilities_to_watch.length > 0 && (
            <div>
              <p className="label mb-1.5">{t('abilitiesToWatch')}</p>
              <ul className="flex flex-col gap-1.5">
                {d.abilities_to_watch.map((a) => (
                  <li key={a.name} className="rounded-md border border-base-700 bg-base-900/50 px-2.5 py-1.5">
                    <p className="text-[11px] font-semibold text-slate-200">
                      {a.name}
                      {a.is_ultimate && <span className="ml-1.5 chip border-gold/50 text-gold">ULT</span>}
                      {a.bkbpierce && <span className="ml-1.5 chip border-dire/50 text-dire">pierces BKB</span>}
                    </p>
                    <p className="mt-0.5 text-[10px] leading-snug text-slate-400">{a.desc}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <Field label={t('whenToFight')} value={d.when_can_fight} />
          <Field label={t('positioning')} value={d.positioning} />
          {d.items_that_help.length > 0 && (
            <div>
              <p className="label mb-1.5">{t('itemsThatHelp')}</p>
              <div className="flex flex-wrap gap-1.5">
                {d.items_that_help.map((i) => (
                  <ItemTip key={i.key} item={i} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function ItemTip({ item }: { item: ItemPick }) {
  const [open, setOpen] = useState(false);
  return (
    <span
      role="button"
      tabIndex={0}
      aria-expanded={open}
      onClick={() => setOpen((v) => !v)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          setOpen((v) => !v);
        }
      }}
      onBlur={() => setOpen(false)}
      className="group relative cursor-pointer rounded-md border border-gold/40 bg-gold/5 px-2 py-1 text-[11px] font-medium text-slate-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-radiant/60"
    >
      {item.name}
      <span
        className={cn(
          'pointer-events-none absolute left-0 top-full z-20 mt-1 w-60 rounded-lg border border-base-600 bg-base-900 p-2 text-[11px] text-slate-300 shadow-xl group-hover:block',
          open ? 'block' : 'hidden',
        )}
      >
        {item.reason}
      </span>
    </span>
  );
}

function SkillStrip({ strategy }: { strategy: HeroStrategy }) {
  const t = useTranslations('report');
  const sb = strategy.skill_build;
  return (
    <>
      <div className="flex flex-wrap gap-1">
        {sb.levels.map((l) => (
          <span
            key={l.level}
            title={`${t('level', { level: l.level })} · ${l.choice} — ${l.reason}`}
            className={cn(
              'flex h-8 w-8 flex-col items-center justify-center rounded-md border text-[10px] font-bold leading-none',
              l.kind === 'ultimate' && 'border-gold/60 bg-gold/15 text-gold',
              l.kind === 'talent' && 'border-magic/60 bg-magic/15 text-magic',
              l.kind === 'stats' && 'border-base-600 bg-base-800 text-slate-400',
              l.kind === 'basic' && 'border-base-600 bg-base-850 text-slate-200',
            )}
          >
            <span className="text-[8px] opacity-60">{l.level}</span>
            {l.kind === 'basic'
              ? l.choice.split(' ').map((w) => w[0]).join('').slice(0, 3)
              : l.kind === 'ultimate'
                ? 'ULT'
                : l.kind === 'talent'
                  ? 'TAL'
                  : 'STAT'}
          </span>
        ))}
      </div>
      <p className="mt-3 flex flex-wrap gap-x-1.5 text-xs text-slate-400">
        <span className="font-semibold text-radiant">{sb.primary}</span>
        <span>{t('maxedFirstSuffix')}</span>
        <span className="font-semibold text-slate-300">{sb.secondary}</span>
        <span>{t('secondSuffix')}</span>
        {sb.ultimate && (
          <>
            <span className="font-semibold text-gold">{sb.ultimate}</span>
            <span>{t('ultimateSuffix')}</span>
          </>
        )}
      </p>
    </>
  );
}

function SectionHeading({ n, title }: { n: number; title: string }) {
  return (
    <h2 className="mb-2 flex items-center gap-2 px-1 text-sm font-bold uppercase tracking-wider text-slate-400">
      <span className="flex h-5 w-5 items-center justify-center rounded bg-base-700 text-[11px] text-slate-300">{n}</span>
      {title}
    </h2>
  );
}

function Bullets({ title, items, tone = 'neutral' }: { title: string; items: string[]; tone?: 'radiant' | 'dire' | 'gold' | 'neutral' }) {
  if (!items || items.length === 0) return null;
  return (
    <div>
      <p className={cn('label mb-1.5', tone === 'radiant' && 'text-radiant', tone === 'dire' && 'text-dire', tone === 'gold' && 'text-gold')}>{title}</p>
      <ul className="flex flex-col gap-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex gap-2 text-xs leading-relaxed text-slate-300">
            <span className={cn('mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full', tone === 'dire' ? 'bg-dire' : tone === 'gold' ? 'bg-gold' : 'bg-radiant')} />
            {it}
          </li>
        ))}
      </ul>
    </div>
  );
}

function Field({ label, value, tone }: { label: string; value: string; tone?: 'danger' }) {
  return (
    <div className="rounded-lg border border-base-700 bg-base-900/40 p-2.5">
      <p className={cn('label mb-1', tone === 'danger' && 'text-dire')}>{label}</p>
      <p className="text-xs leading-relaxed text-slate-300">{value}</p>
    </div>
  );
}

function diffKey(n: number): string {
  return `diff${Math.max(1, Math.min(5, n))}`;
}

function riskKey(risk: string): string {
  return risk === 'high' ? 'riskHigh' : risk === 'low' ? 'riskLow' : 'riskMedium';
}
