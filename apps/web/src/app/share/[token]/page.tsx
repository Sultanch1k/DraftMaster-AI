import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { decodeDraft } from '@/lib/share';
import { heroName } from '@/lib/heroes';
import { ShareView } from '@/components/ShareView';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

/**
 * A share link must never be indexed: it is a personal, ephemeral view of one
 * draft, and indexing thousands of them would be thin, duplicate content.
 */
export async function generateMetadata({ params }: { params: Promise<{ token: string }> }): Promise<Metadata> {
  const { token } = await params;
  const draft = decodeDraft(token);
  const t = await getTranslations('share');
  const enemies = (draft?.e ?? []).map((id) => heroName(id)).filter(Boolean) as string[];
  const pick = draft?.h ? heroName(draft.h) : null;
  const title = pick
    ? `${pick} vs ${enemies.join(', ')} — DraftMaster AI win plan`
    : t('viewTitle');
  const description = pick
    ? `The exact build, kill order and win conditions to beat ${enemies.join(', ')} with ${pick}.`
    : t('viewSub');
  return {
    title,
    description,
    robots: { index: false, follow: true },
    alternates: { canonical: `/share/${token}` },
    openGraph: { title, description, url: `${BASE}/share/${token}`, type: 'article' },
    twitter: { card: 'summary_large_image', title, description },
  };
}

export default async function SharePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  return (
    <main className="mx-auto w-full max-w-[1100px] px-3 py-6 sm:px-6">
      <ShareView token={token} />
    </main>
  );
}
