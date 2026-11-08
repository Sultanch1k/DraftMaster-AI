import type { Metadata } from 'next';
import Link from 'next/link';

// The root layout is dynamic (cookie-based locale), so an unknown slug cannot
// change the HTTP status. Marking it noindex keeps a crawler from indexing the
// dead URL as thin content — the valid hero pages are the only ones sitemapped.
export const metadata: Metadata = {
  title: 'Hero not found',
  robots: { index: false, follow: true },
};

export default function CounterNotFound() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col items-center justify-center gap-4 px-4 text-center">
      <h1 className="text-2xl font-black text-white">That hero page does not exist</h1>
      <p className="text-sm text-slate-400">
        The hero you asked for is not in the current patch dataset.
      </p>
      <Link href="/" className="btn-primary">
        Back to DraftMaster AI
      </Link>
    </main>
  );
}
