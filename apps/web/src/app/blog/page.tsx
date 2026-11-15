import type { Metadata } from 'next';
import Link from 'next/link';
import { allPosts } from '@/lib/blog';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export const metadata: Metadata = {
  title: 'Dota 2 Strategy Blog — Patch Winners, Counters & Meta Reports',
  description:
    'Data-driven Dota 2 strategy articles: patch winners and losers, counter picks, item answers and meta trends, generated from real match data and updated every patch.',
  alternates: { canonical: '/blog' },
  openGraph: {
    title: 'DraftMaster AI — Dota 2 Strategy Blog',
    description: 'Patch winners, counters and meta reports from real match data.',
    url: `${BASE}/blog`,
    type: 'website',
  },
};

function formatDate(iso: string): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

export default function BlogIndex() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <header className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-widest text-radiant">DraftMaster AI</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-white sm:text-4xl">
          Dota 2 Strategy Blog
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-slate-400">
          Patch winners, counter picks and item answers — generated from real match data and
          refreshed every patch.
        </p>
      </header>

      {allPosts.length === 0 ? (
        <p className="text-sm text-slate-400">No articles published yet. Check back soon.</p>
      ) : (
        <ul className="space-y-3">
          {allPosts.map((post) => (
            <li key={post.slug}>
              <Link
                href={`/blog/${post.slug}`}
                className="block rounded-xl border border-base-700 bg-base-900/60 p-4 transition hover:border-radiant/60 hover:bg-base-900"
              >
                <div className="flex items-center gap-2 text-[11px] text-slate-500">
                  <span className="rounded bg-base-800 px-1.5 py-0.5 font-semibold uppercase tracking-wide">
                    {post.locale}
                  </span>
                  <span>{formatDate(post.created_at)}</span>
                </div>
                <h2 className="mt-2 text-base font-bold text-white">{post.title}</h2>
                <p className="mt-1 line-clamp-2 text-sm text-slate-400">{post.excerpt}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-10 rounded-xl border border-radiant/40 bg-radiant/5 p-5 text-center">
        <p className="text-sm font-semibold text-white">Drafting right now?</p>
        <p className="mt-1 text-sm text-slate-400">
          Get a full win plan for your enemy lineup in under five seconds.
        </p>
        <Link
          href="/panic"
          className="mt-3 inline-block rounded-lg bg-radiant px-4 py-2 text-sm font-bold text-base-950 transition hover:bg-radiant-dim"
        >
          🚨 I&apos;m last pick
        </Link>
      </div>
    </main>
  );
}
