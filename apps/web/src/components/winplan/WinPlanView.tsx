'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import type { WinPlanView as WinPlan } from '@/lib/winplan';
import { HeroPortrait } from '../HeroPortrait';
import { WinPlanHeroIdentity, WinPlanStatement } from './HeroIdentity';
import { WinPlanVerdict, WinPlanKillPriority, WinPlanWinCondition, WinPlanMistakes, WinPlanWhy } from './Panels';
import {
  WinPlanItemBuild,
  WinPlanThreats,
  WinPlanPowerSpikes,
  WinPlanDangerHeroes,
  WinPlanPhases,
} from './Tactical';

/**
 * THE WIN PLAN — the central result experience.
 *
 * Mobile-first: the order below is the reading order a player needs mid-draft
 * (who am I, what's the verdict, how do I win, what kills me, what do I build).
 * Desktop expands into editorial columns rather than stretching the mobile stack.
 * Every section renders from the normalized WinPlan view model and omits itself
 * when the engine has nothing to say — no empty panels, no invented values.
 */
export function WinPlanView({
  plan,
  header,
  footer,
}: {
  plan: WinPlan;
  /** Optional controls (share bar) rendered under the identity header. */
  header?: React.ReactNode;
  /** Optional trailing content (backups, usage line). */
  footer?: React.ReactNode;
}) {
  const t = useTranslations('winplan');
  const enemies = useMemo(() => plan.enemyDraft, [plan.enemyDraft]);

  return (
    <div className="flex flex-col gap-3 sm:gap-4">
      <WinPlanHeroIdentity plan={plan} />
      {header}

      {/* Verdict + win condition sit together: the assessment and what it takes to win. */}
      <div className="grid gap-3 sm:gap-4 lg:grid-cols-2">
        <WinPlanVerdict plan={plan} />
        <WinPlanWinCondition conditions={plan.winConditions} />
      </div>

      <WinPlanStatement sentence={plan.mainWinPlan} />

      <WinPlanWhy reasons={plan.whyItWorks} />

      {enemies.length > 0 && (
        <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
          <p className="kicker mb-3">{t('enemyDraft')}</p>
          <div className="flex flex-wrap gap-2.5">
            {enemies.map((h) => (
              <div key={h.id} className="flex items-center gap-2 rounded-lg border border-base-700 bg-base-900/60 px-2 py-1.5">
                <HeroPortrait icon={h.icon} name={h.name} size={28} />
                <span className="text-xs text-ink-soft">{h.name}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="grid gap-3 sm:gap-4 lg:grid-cols-[1.1fr_1fr]">
        <WinPlanKillPriority targets={plan.killPriority} />
        <WinPlanDangerHeroes heroes={plan.dangerHeroes} />
      </div>

      <WinPlanItemBuild build={plan.itemBuild} />

      <WinPlanPowerSpikes spikes={plan.powerSpikes} />

      <WinPlanPhases phases={plan.phases} />

      <WinPlanThreats analysis={plan.threats} />

      <WinPlanMistakes mistakes={plan.mistakes} />

      {footer}
    </div>
  );
}
