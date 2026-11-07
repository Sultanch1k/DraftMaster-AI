import { Loader2 } from 'lucide-react';

/**
 * Loading placeholder that mirrors the report layout, so the page does not jump
 * when results arrive and the wait reads as "the coach is thinking".
 */
export function ReportSkeleton({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-4" aria-busy="true" aria-live="polite">
      <div className="card card-pad flex items-center gap-3 text-sm text-slate-300">
        <Loader2 className="h-4 w-4 animate-spin text-radiant" />
        {label}
      </div>
      <div className="card card-pad animate-pulse">
        <div className="flex items-center gap-3">
          <div className="h-14 w-14 rounded-md bg-base-700" />
          <div className="flex flex-1 flex-col gap-2">
            <div className="h-3 w-24 rounded bg-base-700" />
            <div className="h-5 w-40 rounded bg-base-700" />
            <div className="h-3 w-56 rounded bg-base-700" />
          </div>
        </div>
        <div className="mt-4 h-14 rounded-lg bg-base-800" />
      </div>
      <div className="grid gap-3 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card card-pad animate-pulse">
            <div className="h-4 w-32 rounded bg-base-700" />
            <div className="mt-3 flex flex-col gap-2">
              <div className="h-3 w-full rounded bg-base-800" />
              <div className="h-3 w-5/6 rounded bg-base-800" />
              <div className="h-3 w-2/3 rounded bg-base-800" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
