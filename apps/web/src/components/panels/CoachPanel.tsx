'use client';

import { useState } from 'react';
import { GraduationCap, Loader2, Search } from 'lucide-react';
import { api, ApiError } from '@/lib/api';
import type { CoachReport } from '@/lib/types';
import { cn } from '@/lib/format';
import { Card } from '@/components/Card';

const GRADE_STYLE: Record<string, string> = {
  S: 'text-radiant border-radiant/50 bg-radiant/10',
  A: 'text-radiant border-radiant/40 bg-radiant/5',
  B: 'text-gold border-gold/40 bg-gold/5',
  C: 'text-gold border-gold/50 bg-gold/10',
  D: 'text-dire border-dire/50 bg-dire/10',
  'N/A': 'text-slate-500 border-base-600',
};

export function CoachPanel({ premium, onPremium }: { premium: boolean; onPremium: () => void }) {
  const [matchId, setMatchId] = useState('');
  const [report, setReport] = useState<CoachReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    const id = Number(matchId.trim());
    if (!id || Number.isNaN(id)) {
      setError('Enter a numeric Dota 2 match ID.');
      return;
    }
    setError(null);
    setLoading(true);
    setReport(null);
    try {
      const res = await api.coach(id);
      setReport(res.coach_report);
    } catch (e) {
      setError((e as ApiError).message ?? 'Could not fetch that match.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <Card title="Match ID Coach" icon={<GraduationCap className="h-4 w-4 text-radiant" />} action={<span className="chip">live OpenDota data</span>}>
        <p className="mb-3 text-sm text-slate-400">
          Paste any public match ID. DraftMaster pulls the real match from OpenDota and grades your farm,
          XP, last hits, fighting and survival against benchmarks for your bracket, then gives you a
          practice plan.
        </p>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <input
              value={matchId}
              onChange={(e) => setMatchId(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && run()}
              placeholder="e.g. 9080108550"
              inputMode="numeric"
              className="w-full rounded-lg border border-base-600 bg-base-900/80 py-2.5 pl-9 pr-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-radiant/60 focus:ring-1 focus:ring-radiant/40"
            />
          </div>
          <button type="button" onClick={run} disabled={loading} className="btn-primary">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GraduationCap className="h-4 w-4" />}
            Coach my game
          </button>
        </div>
        {!premium && (
          <p className="mt-2 text-[11px] text-slate-500">
            Free plan includes match coaching previews.{' '}
            <button type="button" onClick={onPremium} className="font-semibold text-gold underline">
              Switch to Premium
            </button>{' '}
            for unlimited coaching.
          </p>
        )}
        {error && <p className="mt-3 rounded-lg border border-dire/50 bg-dire/10 p-2.5 text-sm text-dire">{error}</p>}
      </Card>

      {report && (
        <div className="flex flex-col gap-4">
          <Card>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="label">Match {report.match_id}</p>
                <p className="text-lg font-bold text-white">
                  {report.radiant_win ? 'Radiant victory' : 'Dire victory'} · {report.duration_min} min
                </p>
                <p className="mt-1 text-sm text-slate-300">{report.verdict}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                {Object.entries(report.grades).map(([k, v]) => (
                  <span key={k} className={cn('flex flex-col items-center rounded-lg border px-3 py-1.5', GRADE_STYLE[v] ?? GRADE_STYLE['N/A'])}>
                    <span className="text-[10px] uppercase tracking-wider text-slate-400">{k}</span>
                    <span className="text-lg font-black leading-none">{v}</span>
                  </span>
                ))}
              </div>
            </div>
          </Card>

          <div className="grid gap-4 lg:grid-cols-3">
            <CoachList title="Strengths" items={report.strengths} tone="radiant" />
            <CoachList title="Mistakes" items={report.mistakes} tone="dire" />
            <CoachList title="Item notes" items={report.item_notes} tone="gold" />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <CoachList title="Timing notes" items={report.timing_notes} tone="gold" />
            <CoachList title="Practice plan" items={report.practice_plan} tone="radiant" />
          </div>
        </div>
      )}
    </div>
  );
}

const COACH_TONES: Record<'radiant' | 'dire' | 'gold', string> = {
  radiant: 'border-radiant/40',
  dire: 'border-dire/40',
  gold: 'border-gold/40',
};

function CoachList({ title, items, tone }: { title: string; items: string[]; tone: 'radiant' | 'dire' | 'gold' }) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">Nothing notable.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {items.map((t, i) => (
            <li
              key={i}
              className={cn(
                'rounded-md border bg-base-900/40 px-2.5 py-1.5 text-xs leading-relaxed text-slate-200',
                COACH_TONES[tone],
              )}
            >
              {t}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
