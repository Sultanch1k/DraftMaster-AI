import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { LegalShell, SUPPORT_EMAIL } from '@/components/LegalShell';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('legal');
  return {
    title: t('refundTitle'),
    description: t('refundDescription'),
    alternates: { canonical: '/refund' },
    openGraph: { title: t('refundTitle'), url: `${BASE}/refund`, type: 'article' },
  };
}

export default async function RefundPage() {
  const t = await getTranslations('legal');
  return (
    <LegalShell title={t('refundTitle')}>
      <p>{t('refundIntro')}</p>

      <h2>{t('refundWindowTitle')}</h2>
      <p>{t('refundWindow')}</p>

      <h2>{t('refundHowTitle')}</h2>
      <p>
        {t('refundHow')} <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </p>

      <h2>{t('refundMorTitle')}</h2>
      <p>{t('refundMor')}</p>

      <h2>{t('refundCancelTitle')}</h2>
      <p>{t('refundCancel')}</p>

      <h2>{t('privacyContactTitle')}</h2>
      <p>
        {t('privacyContact')} <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </p>
    </LegalShell>
  );
}
