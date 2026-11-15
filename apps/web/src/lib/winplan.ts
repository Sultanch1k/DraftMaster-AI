import type {
  HeroStrategy,
  ItemBuild,
  ItemPick,
  PanicResult,
  PowerSpike,
  Report,
  TargetRow,
  ThreatAnalysis,
  WinConditions,
} from './types';
import { heroArt } from './heroes';

/**
 * Normalized Win Plan view model.
 *
 * This is a *presentation* layer: it reshapes the engine's already-computed
 * output into one shape the website, the social export and the public share page
 * can all render. It performs no strategy maths and invents nothing — every
 * field maps onto a real engine field. Where the engine does not provide a
 * value, the field is optional and the UI omits it rather than faking it.
 */

export type WinPlanMode = 'counter' | 'strategy';

/** Honest categorical draft assessment. Never a fabricated probability. */
export type DraftVerdictKind = 'favorable' | 'competitive' | 'difficult' | 'situational';

export type WinPlanTarget = {
  rank: number;
  heroId: number;
  name: string;
  reason: string;
  score: number;
};

export type WinPlanView = {
  mode: WinPlanMode;
  heroId: number;
  heroName: string;
  heroIcon?: string | null;
  /** Full-bleed artwork path for the hero identity header. */
  heroArt?: string | null;
  roles: string[];
  role?: string | null;
  rank?: string | null;
  patch?: string | null;
  generatedInMs: number;

  verdict: {
    kind: DraftVerdictKind;
    /** Present only because the engine models it explicitly; labelled as an estimate. */
    winProbability?: number;
    confidence?: string;
    /** Localized engine prose (e.g. the matchup assessment). */
    assessment: string;
  };

  /** The single sentence that answers "how do I win this game?". */
  mainWinPlan: string;
  whyItWorks: string[];
  winConditions: WinConditions;
  killPriority: WinPlanTarget[];
  powerSpikes: { player: PowerSpike[]; enemies: PowerSpike[] };
  itemBuild: ItemBuild;
  threats: ThreatAnalysis;
  /** The enemies most able to break the plan. */
  dangerHeroes: WinPlanTarget[];
  /** Concrete mistakes to avoid, sourced from the engine. */
  mistakes: string[];
  itemAvoid: ItemPick[];
  /** Phase guidance, when the engine provides a timeline (counter mode). */
  phases: { window: string; phase: string; objectives: string[]; farmFocus: string; fightFocus: string; mapMovement: string; dangerZones: string[] }[];
  enemyDraft: { id: number; name: string; icon?: string | null }[];

  /** Lane label when the engine supports it (strategy mode). */
  lane?: string | null;
};

function verdictFor(probability: number | undefined): DraftVerdictKind {
  if (probability === undefined) return 'situational';
  if (probability >= 54) return 'favorable';
  if (probability >= 47) return 'competitive';
  return 'difficult';
}

function toTargets(rows: TargetRow[]): WinPlanTarget[] {
  return [...rows]
    .sort((a, b) => a.rank - b.rank)
    .map((r) => ({
      rank: r.rank,
      heroId: r.hero_id,
      name: r.name,
      reason: r.reason,
      score: r.priority_score,
    }));
}

/** Counter-Pick / Panic ("I'm last pick"). */
export function fromPanic(result: PanicResult): WinPlanView {
  const hero = result.best_hero;
  const probability = result.win_probability?.player_win_probability;
  return {
    mode: 'counter',
    heroId: hero.hero_id,
    heroName: hero.localized_name,
    heroIcon: hero.icon,
    heroArt: heroArt(hero.hero_id),
    roles: hero.roles,
    generatedInMs: result.generated_in_ms,
    verdict: {
      kind: verdictFor(probability),
      winProbability: probability,
      confidence: result.win_probability?.confidence,
      assessment: result.win_probability?.verdict ?? result.one_sentence_win_plan,
    },
    mainWinPlan: result.one_sentence_win_plan,
    whyItWorks: result.why_this_hero,
    winConditions: result.win_conditions,
    killPriority: toTargets(result.kill_priority),
    powerSpikes: result.power_spikes,
    itemBuild: result.full_build,
    threats: result.threat_analysis,
    dangerHeroes: toTargets(result.danger_heroes),
    mistakes: result.items_to_avoid.map((i) => `${i.name}: ${i.reason}`),
    itemAvoid: result.items_to_avoid,
    phases: [],
    enemyDraft: [],
  };
}

/** Full 11-section counter report for a specific pick. */
export function fromReport(report: Report): WinPlanView {
  const heroName = report.draft_summary.hero ?? '';
  const pick = report.best_picks.find((p) => p.localized_name === heroName) ?? report.best_picks[0];
  const probability = report.win_probability?.player_win_probability;
  const heroId = pick?.hero_id ?? 0;
  return {
    mode: 'counter',
    heroId,
    heroName: heroName || pick?.localized_name || '',
    heroIcon: pick?.icon ?? null,
    heroArt: heroId ? heroArt(heroId) : null,
    roles: pick?.roles ?? [],
    role: report.role ?? null,
    rank: report.rank ?? null,
    patch: report.patch ?? null,
    generatedInMs: report.generated_in_ms,
    verdict: {
      kind: verdictFor(probability),
      winProbability: probability,
      confidence: report.win_probability?.confidence,
      assessment: report.draft_summary.verdict || report.win_probability?.verdict || '',
    },
    mainWinPlan: report.one_sentence_win_plan,
    whyItWorks: report.why_this_hero,
    winConditions: report.win_conditions,
    killPriority: toTargets(report.target_priority),
    powerSpikes: report.power_spikes,
    itemBuild: report.item_build,
    threats: report.threat_analysis,
    dangerHeroes: toTargets(report.target_priority).slice(0, 3),
    mistakes: report.item_build.avoid.map((i) => `${i.name}: ${i.reason}`),
    itemAvoid: report.item_build.avoid,
    phases: report.match_plan.map((p) => ({
      window: p.window,
      phase: p.phase,
      objectives: p.objectives,
      farmFocus: p.farm_focus,
      fightFocus: p.fight_focus,
      mapMovement: p.map_movement,
      dangerZones: p.danger_zones,
    })),
    enemyDraft: report.enemy_draft.map((h) => ({ id: h.id, name: h.localized_name, icon: h.icon })),
  };
}

/** My Hero Strategy. */
export function fromHeroStrategy(strategy: HeroStrategy): WinPlanView {
  const hero = strategy.hero;
  const probability = strategy.matchup_overview?.win_probability ?? strategy.win_probability?.player_win_probability;
  const danger: WinPlanTarget[] = (strategy.enemy_dossiers ?? []).slice(0, 3).map((d, i) => ({
    rank: i + 1,
    heroId: d.hero_id,
    name: d.name,
    reason: d.what_makes_dangerous?.[0] ?? d.when_can_fight ?? '',
    score: d.danger_score,
  }));
  const mistakes = [...(strategy.matchup_overview?.biggest_mistakes ?? [])];
  return {
    mode: 'strategy',
    heroId: hero.id,
    heroName: hero.localized_name,
    heroIcon: hero.icon,
    heroArt: heroArt(hero.id),
    roles: hero.roles,
    role: strategy.role ?? null,
    rank: strategy.rank ?? null,
    patch: strategy.patch ?? null,
    lane: strategy.lane_strategy?.lane ?? hero.lane ?? null,
    generatedInMs: strategy.generated_in_ms,
    verdict: {
      kind: verdictFor(probability),
      winProbability: probability,
      confidence: strategy.matchup_overview?.confidence ?? strategy.win_probability?.confidence,
      assessment: strategy.matchup_overview?.assessment ?? '',
    },
    mainWinPlan: strategy.one_sentence_game_plan,
    whyItWorks: strategy.matchup_overview?.advantages ?? [],
    winConditions: strategy.win_conditions,
    killPriority: toTargets(strategy.target_priority ?? []),
    powerSpikes: strategy.power_spikes,
    itemBuild: strategy.item_build,
    threats: strategy.threat_analysis,
    dangerHeroes: danger,
    mistakes,
    itemAvoid: strategy.item_build.avoid,
    phases: [],
    enemyDraft: strategy.enemy_draft.map((h) => ({ id: h.id, name: h.localized_name, icon: h.icon })),
  };
}
