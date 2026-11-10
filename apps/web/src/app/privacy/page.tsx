import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { LegalShell, SUPPORT_EMAIL } from '@/components/LegalShell';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('legal');
  return {
    title: t('privacyTitle'),
    description: t('privacyDescription'),
    alternates: { canonical: '/privacy' },
    openGraph: { title: t('privacyTitle'), url: `${BASE}/privacy`, type: 'article' },
  };
}

export default async function PrivacyPage() {
  const t = await getTranslations('legal');
  return (
    <LegalShell title={t('privacyTitle')}>
      <p>{t('privacyIntro')}</p>

      <h2>{t('privacyDataTitle')}</h2>
      <p>{t('privacyData')}</p>

      <h2>{t('privacyUseTitle')}</h2>
      <p>{t('privacyUse')}</p>

      <h2>{t('privacyPaymentsTitle')}</h2>
      <p>{t('privacyPayments')}</p>

      <h2>{t('privacyThirdTitle')}</h2>
      <p>{t('privacyThird')}</p>

      <h2>{t('privacyRetentionTitle')}</h2>
      <p>{t('privacyRetention')}</p>

      <h2>{t('privacyRightsTitle')}</h2>
      <p>
        {t('privacyRights')}{' '}
        <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </p>

      <h2>{t('privacyContactTitle')}</h2>
      <p>
        {t('privacyContact')} <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </p>
    </LegalShell>
  );
}
