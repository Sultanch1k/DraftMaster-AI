import { Loader2 } from 'lucide-react';

export default function Loading() {
  return (
    <div className="flex min-h-dvh items-center justify-center gap-3 text-sm text-slate-300">
      <Loader2 className="h-5 w-5 animate-spin text-radiant" />
      DraftMaster AI
    </div>
  );
}
