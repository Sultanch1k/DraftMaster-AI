import type { Metadata } from 'next';
import { getTranslations } from 'next-intl/server';
import { LegalShell, SUPPORT_EMAIL } from '@/components/LegalShell';

const BASE = process.env.NEXT_PUBLIC_SITE_URL || 'https://www.draftmaster.wiki';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('legal');
  return {
    title: t('termsTitle'),
    description: t('termsDescription'),
    alternates: { canonical: '/terms' },
    openGraph: { title: t('termsTitle'), url: `${BASE}/terms`, type: 'article' },
  };
}

export default async function TermsPage() {
  const t = await getTranslations('legal');
  return (
    <LegalShell title={t('termsTitle')}>
      <p>{t('termsIntro')}</p>

      <h2>{t('termsServiceTitle')}</h2>
      <p>{t('termsService')}</p>

      <h2>{t('termsNotAffiliatedTitle')}</h2>
      <p>{t('termsNotAffiliated')}</p>

      <h2>{t('termsPlansTitle')}</h2>
      <p>{t('termsPlans')}</p>

      <h2>{t('termsAcceptableTitle')}</h2>
      <p>{t('termsAcceptable')}</p>

      <h2>{t('termsDisclaimerTitle')}</h2>
      <p>{t('termsDisclaimer')}</p>

      <h2>{t('termsLiabilityTitle')}</h2>
      <p>{t('termsLiability')}</p>

      <h2>{t('privacyContactTitle')}</h2>
      <p>
        {t('privacyContact')} <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>
      </p>
    </LegalShell>
  );
}
