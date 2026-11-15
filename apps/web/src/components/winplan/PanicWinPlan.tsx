'use client';

import { useTranslations } from 'next-intl';
import type { PanicResult } from '@/lib/types';
import { fromPanic } from '@/lib/winplan';
import { HeroPortrait } from '../HeroPortrait';
import { ShareBar } from '../ShareBar';
import { WinPlanView } from './WinPlanView';
import { PosterExport } from './PosterExport';

/**
 * "I'M LAST PICK" result, rendered through the shared Win Plan system.
 *
 * The mode-specific chrome (backups, usage, jump to the full report) lives here;
 * the strategy content is the same WinPlanView the full report and share page use.
 */
export function PanicWinPlan({
  result,
  enemyIds,
  role,
  rank,
  onFullReport,
  onQuota,
}: {
  result: PanicResult;
  enemyIds: number[];
  role?: string;
  rank?: number;
  onFullReport?: () => void;
  onQuota?: () => void;
}) {
  const t = useTranslations('panic');
  const tShare = useTranslations('winplan.share');
  const tVerdict = useTranslations('winplan.verdictKind');
  const plan = fromPanic(result);
  const query = new URLSearchParams();
  if (enemyIds.length) query.set('e', enemyIds.join(','));
  if (role) query.set('role', role);
  if (rank) query.set('rk', String(rank));

  return (
    <WinPlanView
      plan={plan}
      header={
        <div className="flex flex-wrap items-center gap-2">
          <ShareBar enemyIds={enemyIds} role={role} rank={rank} onQuota={onQuota} />
        </div>
      }
      footer={
        <>
          <PosterExport
            posterBase={`/og/poster?${query.toString()}`}
            filename={`draftmaster-${plan.heroId}-${plan.heroName.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
            caption={tShare('caption', {
              hero: plan.heroName,
              verdict: tVerdict(plan.verdict.kind),
              plan: plan.mainWinPlan,
            })}
          />

          {result.backups.length > 0 && (
            <section className="rounded-panel border border-base-700 bg-base-850 p-4 sm:p-5">
              <p className="label mb-2">{t('backups')}</p>
              <div className="flex flex-wrap gap-2">
                {result.backups.slice(0, 4).map((p, i) => (
                  <div key={p.hero_id} className="flex items-center gap-2 rounded-lg border border-base-700 bg-base-900/60 px-2 py-1.5">
                    <span className="tabular text-[10px] font-bold text-ink-faint">#{i + 2}</span>
                    <HeroPortrait icon={p.icon} name={p.localized_name} size={26} />
                    <span className="text-xs text-ink-soft">{p.localized_name}</span>
                    <span className="tabular text-[10px] text-ink-faint">{p.final_score.toFixed(0)}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-faint">
            <span>
              {t('generatedIn', { ms: result.generated_in_ms })}
              {result.usage && (
                <>
                  {' · '}
                  {result.usage.plan === 'premium' ? t('premiumPlan') : t('freePlan')}
                  {result.usage.remaining != null && ` · ${t('analysesLeft', { count: result.usage.remaining })}`}
                </>
              )}
            </span>
            {onFullReport && (
              <button type="button" onClick={onFullReport} className="btn-ghost !py-1.5 text-xs">
                {t('openFull')}
              </button>
            )}
          </div>
        </>
      }
    />
  );
}
