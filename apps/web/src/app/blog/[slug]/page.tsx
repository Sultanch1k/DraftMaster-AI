import type { Metadata } from 'next';
import Link from 'next/link';
import { notFound } from 'next/navigation';
import { allPosts, getPost } from '@/lib/blog';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export function generateStaticParams() {
  return allPosts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) return {};
  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/blog/${post.slug}` },
    openGraph: {
      title: post.title,
      description: post.excerpt,
      url: `${BASE}/blog/${post.slug}`,
      type: 'article',
    },
    twitter: { card: 'summary', title: post.title, description: post.excerpt },
  };
}

const URL_RE = /(https?:\/\/[^\s]+)/g;

function renderLine(line: string, key: number) {
  const parts = line.split(URL_RE);
  return (
    <p key={key} className="text-sm leading-relaxed text-ink-soft">
      {parts.map((part, i) =>
        URL_RE.test(part) ? (
          <a
            key={i}
            href={part}
            className="text-radiant underline underline-offset-2"
            rel="noopener noreferrer"
          >
            {part}
          </a>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </p>
  );
}

function renderBody(body: string) {
  const blocks = body.split(/\n{2,}/).filter((b) => b.trim());
  return blocks.map((block, bi) => {
    const lines = block.split('\n').map((l) => l.trim()).filter(Boolean);
    if (lines.every((l) => l.startsWith('• ') || l.startsWith('- '))) {
      return (
        <ul key={bi} className="my-3 space-y-1.5 pl-1">
          {lines.map((l, li) => (
            <li key={li} className="flex gap-2 text-sm text-ink-soft">
              <span className="text-radiant">•</span>
              <span>{l.replace(/^[•-]\s*/, '')}</span>
            </li>
          ))}
        </ul>
      );
    }
    return (
      <div key={bi} className="my-3 space-y-1.5">
        {lines.map((l, li) => renderLine(l, li))}
      </div>
    );
  });
}

export default async function BlogPostPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const post = getPost(slug);
  if (!post) notFound();

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: post.title,
    datePublished: post.created_at,
    inLanguage: post.locale,
    publisher: { '@type': 'Organization', name: 'DraftMaster AI' },
    mainEntityOfPage: `${BASE}/blog/${post.slug}`,
  };

  return (
    <main className="mx-auto max-w-3xl px-4 py-10 sm:px-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <nav className="mb-6 text-xs text-ink-faint">
        <Link href="/blog" className="hover:text-radiant">
          ← All articles
        </Link>
      </nav>
      <article>
        <h1 className="text-2xl font-black tracking-tight text-ink sm:text-3xl">{post.title}</h1>
        <div className="mt-2 flex items-center gap-2 text-[11px] text-ink-faint">
          <span className="rounded bg-base-800 px-1.5 py-0.5 font-semibold uppercase tracking-wide">
            {post.locale}
          </span>
          <time dateTime={post.created_at}>{post.created_at.slice(0, 10)}</time>
        </div>
        <div className="mt-6">{renderBody(post.body)}</div>
      </article>

      <div className="mt-10 rounded-xl border border-radiant/40 bg-radiant/5 p-5 text-center">
        <p className="text-sm font-semibold text-ink">Want this for your exact draft?</p>
        <p className="mt-1 text-sm text-ink-muted">
          Enter the enemy heroes and get a full win plan in under five seconds.
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
