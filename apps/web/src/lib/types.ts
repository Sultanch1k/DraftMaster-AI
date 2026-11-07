// Shared API types, mirroring the FastAPI response models.

export type Hero = {
  id: number;
  name: string;
  localized_name: string;
  roles: string[];
  primary_attr?: string | null;
  attack_type?: string | null;
  icon?: string | null;
  img?: string | null;
  tags: string[];
  pub_winrate?: number | null;
};

export type ItemPick = {
  key: string;
  name: string;
  cost?: number | null;
  img?: string | null;
  reason: string;
  source: 'meta' | 'counter' | string;
  phase?: string;
};

export type ItemBuild = {
  hero: string;
  starting: ItemPick[];
  lane: ItemPick[];
  early: ItemPick[];
  mid: ItemPick[];
  late: ItemPick[];
  luxury: ItemPick[];
  situational: ItemPick[];
  emergency: ItemPick[];
  avoid: ItemPick[];
  key_counters: ItemPick[];
};

export type HeroScores = {
  counter: number;
  meta: number;
  comfort: number;
  synergy: number;
  difficulty: number;
  lane: number;
  role: number;
  final: number;
};

export type PickCandidate = {
  hero_id: number;
  name: string;
  localized_name: string;
  icon?: string | null;
  img?: string | null;
  roles: string[];
  scores: HeroScores;
  final_score: number;
  reasons: string[];
  countered_by: string[];
  strong_against: string[];
};

export type WinProbability = {
  player_win_probability: number;
  enemy_win_probability: number;
  confidence: 'low' | 'medium' | 'high' | string;
  factors: { name: string; detail: string; contribution_pp: number }[];
  rank_label: string;
  verdict: string;
};

export type ThreatAnalysis = {
  scores: Record<string, number>;
  labels: Record<string, string>;
  danger: Record<string, 'low' | 'medium' | 'high' | string>;
  problems: Record<string, number>;
};

export type TargetRow = {
  hero_id: number;
  name: string;
  priority_score: number;
  threat_to_you: number;
  disables: number;
  roles: string[];
  rank: number;
  reason: string;
};

export type PowerSpike = {
  type?: string;
  when?: string;
  detail?: string;
  hero_id?: number;
  name?: string;
  peak_minutes?: number;
  peak_winrate?: number;
  danger?: string;
};

export type MatchPhase = {
  window: string;
  phase: string;
  objectives: string[];
  farm_focus: string;
  fight_focus: string;
  map_movement: string;
  tower_priority: string;
  roshan_priority: string;
  danger_zones: string[];
};

export type SkillLevel = {
  level: number;
  choice: string;
  reason: string;
  kind: 'basic' | 'ultimate' | 'talent' | 'stats';
};

export type SkillBuild = {
  levels: SkillLevel[];
  notes: string[];
  primary: string;
  secondary: string;
  ultimate: string | null;
};

export type TalentRow = {
  hero_level: number;
  options: string[];
  recommended: string;
  reason: string;
};

export type WinConditions = { primary: string; secondary: string; emergency: string };

export type Report = {
  generated_in_ms: number;
  patch?: string | null;
  enemy_draft: Hero[];
  role?: string | null;
  rank?: string | null;
  win_probability: WinProbability;
  best_picks: PickCandidate[];
  why_this_hero: string[];
  threat_analysis: ThreatAnalysis;
  item_build: ItemBuild;
  skill_build: SkillBuild;
  talents: TalentRow[];
  match_plan: MatchPhase[];
  win_conditions: WinConditions;
  target_priority: TargetRow[];
  power_spikes: { player: PowerSpike[]; enemies: PowerSpike[] };
  one_sentence_win_plan: string;
  draft_summary: {
    headline_threats: { dimension: string; score: number; danger: string }[];
    top_target: string;
    win_probability: number;
    hero?: string;
    verdict: string;
  };
};

export type PanicResult = {
  best_hero: PickCandidate;
  backups: PickCandidate[];
  win_probability: WinProbability;
  full_build: ItemBuild;
  danger_heroes: TargetRow[];
  power_spikes: { player: PowerSpike[]; enemies: PowerSpike[] };
  kill_priority: TargetRow[];
  win_conditions: WinConditions;
  items_to_avoid: ItemPick[];
  one_sentence_win_plan: string;
  why_this_hero: string[];
  threat_analysis: ThreatAnalysis;
  generated_in_ms: number;
  usage?: Usage;
};

export type Usage = {
  plan: 'free' | 'premium';
  used_today: number;
  daily_limit: number | null;
  remaining: number | null;
};

export type Detection = {
  hero_id: number;
  localized_name: string;
  confidence: number;
  margin: number;
  x: number;
  y: number;
  size: number;
};

export type ScreenshotResult = {
  detection: {
    detected: Detection[];
    hero_ids: number[];
    count: number;
    image_size: { width: number; height: number };
    confidence_floor: number;
    confidence_margin: number;
  };
  report: Report | null;
  usage?: Usage;
  note: string;
};

export type CoachReport = {
  match_id: number;
  duration_min: number;
  radiant_win: boolean;
  player: Record<string, unknown>;
  verdict: string;
  grades: Record<string, string>;
  strengths: string[];
  mistakes: string[];
  item_notes: string[];
  timing_notes: string[];
  practice_plan: string[];
};

export type Meta = {
  patch?: string | null;
  generated_at?: string | null;
  source: string;
  trending: { hero_id: number; hero: string; picks: number }[];
  patch_winners: { hero_id: number; hero: string; cm_winrate: number }[];
  patch_losers: { hero_id: number; hero: string; cm_winrate: number }[];
};

export type Role = 'carry' | 'mid' | 'offlane' | 'support' | 'hard_support';
