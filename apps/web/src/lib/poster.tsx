import type { WinPlanView } from './winplan';
import { cdn } from './format';
import { OG } from './og-fonts';

/**
 * Social poster composition.
 *
 * The poster is rendered as an image on the server (Next `next/og` / Satori)
 * rather than drawn on a canvas in the browser. That is a deliberate choice:
 * Valve's hero CDN sends `Access-Control-Allow-Origin: https://www.dota2.com`,
 * so a client-side canvas would be tainted and could not export. Rendering on
 * the server lets the poster include real hero artwork, which is what makes a
 * shared poster look like a product rather than a screenshot.
 *
 * Everything here is plain inline styling — Satori does not read Tailwind
 * classes — and every multi-child node sets `display: flex`, which Satori
 * requires.
 */

type Locale = 'en' | 'ru';

const LABELS: Record<Locale, Record<string, string>> = {
  en: {
    winPlan: 'THE WIN PLAN',
    lastPick: "I'M LAST PICK",
    myHero: 'MY HERO PLAN',
    verdict: 'DRAFT VERDICT',
    estimate: 'draft-edge score · heuristic',
    winCondition: 'WIN CONDITION',
    primary: 'PRIMARY',
    secondary: 'SECONDARY',
    emergency: 'EMERGENCY',
    counters: 'KEY COUNTER ITEMS',
    build: 'CORE BUILD',
    killOrder: 'KILL ORDER',
    danger: 'DANGER HEROES',
    avoid: "DON'T DO THIS",
    cta: 'Get your own win plan in 5 seconds',
    site: 'draftmaster.wiki',
  },
  ru: {
    winPlan: 'ПЛАН НА ИГРУ',
    lastPick: 'Я ПОСЛЕДНИЙ ПИК',
    myHero: 'ПЛАН ДЛЯ МОЕГО ГЕРОЯ',
    verdict: 'ОЦЕНКА ДРАФТА',
    estimate: 'оценка драфта · эвристика',
    winCondition: 'УСЛОВИЕ ПОБЕДЫ',
    primary: 'ОСНОВНОЕ',
    secondary: 'ДОПОЛНИТЕЛЬНОЕ',
    emergency: 'ЗАПАСНОЕ',
    counters: 'КОНТР-ПРЕДМЕТЫ',
    build: 'СБОРКА',
    killOrder: 'ПОРЯДОК УБИЙСТВ',
    danger: 'ОПАСНЫЕ ГЕРОИ',
    avoid: 'НЕ ДЕЛАЙТЕ ТАК',
    cta: 'Получите свой план на игру за 5 секунд',
    site: 'draftmaster.wiki',
  },
};

const VERDICT_KIND: Record<Locale, Record<string, string>> = {
  en: { favorable: 'FAVORABLE', competitive: 'COMPETITIVE', difficult: 'DIFFICULT', situational: 'SITUATIONAL' },
  ru: { favorable: 'В ВАШУ ПОЛЬЗУ', competitive: 'РАВНЫЙ', difficult: 'ТЯЖЕЛО', situational: 'СИТУАТИВНО' },
};

export type PosterData = {
  locale: Locale;
  kicker: string;
  heroName: string;
  heroArtUrl: string | null;
  heroIconUrl: string | null;
  verdictLabel: string;
  winProbability?: number;
  winProbabilityLabel: string;
  winPlan: string;
  winCondition: { primary: string; secondary: string; emergency: string };
  counterItems: { name: string; icon: string | null }[];
  coreBuild: { name: string; icon: string | null }[];
  killOrder: { rank: number; name: string; reason: string }[];
  danger: string[];
  mistakes: string[];
  labels: Record<string, string>;
};

function trim(text: string, max: number): string {
  if (text.length <= max) return text;
  const cut = text.slice(0, max);
  const lastSpace = cut.lastIndexOf(' ');
  return `${(lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}

function itemIcon(img?: string | null): string | null {
  return img ? cdn(img) : null;
}

export function buildPosterData(plan: WinPlanView, locale: Locale): PosterData {
  const labels = LABELS[locale];
  const verdictKind = VERDICT_KIND[locale];
  const core = [...plan.itemBuild.early, ...plan.itemBuild.mid]
    .filter((i, idx, arr) => arr.findIndex((x) => x.key === i.key) === idx)
    .slice(0, 5);
  const counters = (plan.itemBuild.key_counters ?? []).slice(0, 4);
  return {
    locale,
    kicker: plan.mode === 'counter' ? labels.lastPick : labels.myHero,
    heroName: plan.heroName,
    heroArtUrl: plan.heroArt ? cdn(plan.heroArt) : null,
    heroIconUrl: plan.heroIcon ? cdn(plan.heroIcon) : null,
    verdictLabel: verdictKind[plan.verdict.kind] ?? '',
    winProbability: plan.verdict.winProbability,
    winProbabilityLabel: labels.estimate,
    winPlan: plan.mainWinPlan,
    winCondition: {
      primary: plan.winConditions.primary,
      secondary: plan.winConditions.secondary,
      emergency: plan.winConditions.emergency,
    },
    counterItems: counters.map((i) => ({ name: i.name, icon: itemIcon(i.img) })),
    coreBuild: core.map((i) => ({ name: i.name, icon: itemIcon(i.img) })),
    killOrder: plan.killPriority.slice(0, 3).map((t) => ({ rank: t.rank, name: t.name, reason: trim(t.reason, 58) })),
    danger: plan.dangerHeroes.slice(0, 3).map((d) => d.name),
    mistakes: plan.mistakes.slice(0, 2).map((m) => trim(m, 96)),
    labels,
  };
}

// --- shared fragments -------------------------------------------------------

function BrandBar({ labels }: { labels: Record<string, string> }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div
          style={{
            width: 46,
            height: 46,
            borderRadius: 12,
            background: `linear-gradient(135deg, ${OG.accent}, ${OG.accentBright})`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#FFFFFF',
            fontSize: 26,
            fontWeight: 900,
          }}
        >
          D
        </div>
        <div style={{ display: 'flex', fontSize: 30, fontWeight: 700, color: OG.ink, letterSpacing: -0.5 }}>
          DraftMaster&nbsp;<span style={{ color: OG.accentBright }}>AI</span>
        </div>
      </div>
      <div style={{ display: 'flex', fontSize: 22, color: OG.faint }}>{labels.site}</div>
    </div>
  );
}

function SectionTitle({ children, color = OG.accent }: { children: string; color?: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
      <div style={{ display: 'flex', width: 5, height: 22, borderRadius: 3, background: color }} />
      <div style={{ display: 'flex', fontSize: 22, fontWeight: 700, letterSpacing: 2, color }}>{children}</div>
    </div>
  );
}

function HeroBand({ data, height, big }: { data: PosterData; height: number; big: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        position: 'relative',
        width: '100%',
        height,
        borderRadius: 22,
        overflow: 'hidden',
        border: `1px solid ${OG.border}`,
        background: data.heroArtUrl ? `url(${data.heroArtUrl})` : OG.elevated,
        backgroundSize: 'cover',
        backgroundPosition: 'center 18%',
      }}
    >
      <div
        style={{
          display: 'flex',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'linear-gradient(180deg, rgba(9,11,16,0.30) 0%, rgba(9,11,16,0.72) 48%, rgba(9,11,16,0.97) 100%)',
        }}
      />
      <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', width: '100%', padding: 34 }}>
        <div style={{ display: 'flex', fontSize: 22, fontWeight: 700, letterSpacing: 3, color: OG.accentBright, marginBottom: 10 }}>
          {data.kicker}
        </div>
        <div style={{ display: 'flex', fontSize: big ? 108 : 78, fontWeight: 900, color: '#FFFFFF', lineHeight: 1, letterSpacing: -3, fontFamily: 'Playfair Display' }}>
          {data.heroName}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginTop: 18 }}>
          <div
            style={{
              display: 'flex',
              padding: '8px 18px',
              borderRadius: 10,
              border: `1px solid ${OG.accent}88`,
              background: 'rgba(200,54,47,0.14)',
              color: OG.accentBright,
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: 1,
            }}
          >
            {data.verdictLabel}
          </div>
          {typeof data.winProbability === 'number' && (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <div style={{ display: 'flex', fontSize: 40, fontWeight: 900, color: OG.ink, fontFamily: 'Playfair Display' }}>
                {data.winProbability.toFixed(0)}/100
              </div>
              <div style={{ display: 'flex', fontSize: 18, color: OG.faint }}>{data.winProbabilityLabel}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WinPlanBlock({ data, size }: { data: PosterData; size: number }) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        padding: 30,
        borderRadius: 20,
        border: `1px solid ${OG.accent}66`,
        background: 'linear-gradient(135deg, rgba(200,54,47,0.12), rgba(17,21,29,1))',
      }}
    >
      <SectionTitle>{data.labels.winPlan}</SectionTitle>
      <div style={{ display: 'flex', fontSize: size, fontWeight: 700, color: OG.ink, lineHeight: 1.28, fontFamily: 'Playfair Display' }}>
        {data.winPlan}
      </div>
    </div>
  );
}

function ItemRow({ title, items, color, iconSize }: { title: string; items: PosterData['coreBuild']; color: string; iconSize: number }) {
  if (items.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <SectionTitle color={color}>{title}</SectionTitle>
      <div style={{ display: 'flex', gap: 14 }}>
        {items.map((i) => (
          <div key={i.name} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: iconSize + 30 }}>
            {i.icon ? (
              <img
                src={i.icon}
                width={iconSize}
                height={iconSize}
                style={{ borderRadius: 10, border: `1px solid ${OG.border}` }}
                alt=""
              />
            ) : (
              <div style={{ display: 'flex', width: iconSize, height: iconSize, borderRadius: 10, background: OG.elevated, border: `1px solid ${OG.border}` }} />
            )}
            <div style={{ display: 'flex', marginTop: 8, fontSize: 17, color: OG.inkSoft, textAlign: 'center', lineHeight: 1.15 }}>
              {i.name}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KillOrder({ data, compact }: { data: PosterData; compact: boolean }) {
  if (data.killOrder.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <SectionTitle color={OG.dire}>{data.labels.killOrder}</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.killOrder.map((k) => (
          <div key={k.rank} style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                display: 'flex',
                width: 40,
                height: 40,
                borderRadius: 9,
                border: `1px solid ${OG.dire}88`,
                background: 'rgba(217,72,77,0.12)',
                color: OG.dire,
                fontSize: 22,
                fontWeight: 900,
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {k.rank}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              <div style={{ display: 'flex', fontSize: 26, fontWeight: 700, color: OG.ink }}>{k.name}</div>
              {!compact && <div style={{ display: 'flex', fontSize: 18, color: OG.muted }}>{k.reason}</div>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WinConditionBlock({ data, limit }: { data: PosterData; limit: number }) {
  const rows = [
    { label: data.labels.primary, value: trim(data.winCondition.primary, limit), color: OG.radiant },
    { label: data.labels.secondary, value: trim(data.winCondition.secondary, limit), color: OG.gold },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <SectionTitle color={OG.radiant}>{data.labels.winCondition}</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {rows.map((r) => (
          <div
            key={r.label}
            style={{
              display: 'flex',
              flexDirection: 'column',
              padding: 16,
              borderRadius: 12,
              border: `1px solid ${r.color}55`,
              background: 'rgba(23,29,39,0.8)',
            }}
          >
            <div style={{ display: 'flex', fontSize: 16, fontWeight: 700, letterSpacing: 2, color: r.color, marginBottom: 6 }}>
              {r.label}
            </div>
            <div style={{ display: 'flex', fontSize: 22, color: OG.inkSoft, lineHeight: 1.3 }}>{r.value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AvoidBlock({ data }: { data: PosterData }) {
  if (data.mistakes.length === 0) return null;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
      <SectionTitle color={OG.dire}>{data.labels.avoid}</SectionTitle>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {data.mistakes.map((m, i) => (
          <div key={i} style={{ display: 'flex', fontSize: 21, color: OG.inkSoft, lineHeight: 1.3 }}>
            •&nbsp;{m}
          </div>
        ))}
      </div>
    </div>
  );
}

function Footer({ data, big }: { data: PosterData; big: boolean }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        width: '100%',
        padding: '22px 30px',
        borderRadius: 18,
        background: `linear-gradient(135deg, ${OG.accent}, ${OG.accentBright})`,
      }}
    >
      <div style={{ display: 'flex', fontSize: big ? 30 : 24, fontWeight: 700, color: '#FFFFFF' }}>{data.labels.cta}</div>
      <div style={{ display: 'flex', fontSize: big ? 28 : 22, fontWeight: 900, color: '#FFFFFF', letterSpacing: -0.5 }}>
        {data.labels.site}
      </div>
    </div>
  );
}

// --- layouts ----------------------------------------------------------------

const frame = {
  display: 'flex' as const,
  flexDirection: 'column' as const,
  width: '100%',
  height: '100%',
  padding: 54,
  gap: 26,
  backgroundColor: OG.bg,
  color: OG.ink,
  fontFamily: 'Inter',
};

/** 1080×1920 — Instagram/TikTok Story, the primary viral surface. */
export function renderStory(data: PosterData) {
  return (
    <div style={frame}>
      <BrandBar labels={data.labels} />
      <HeroBand data={data} height={400} big />
      <WinPlanBlock data={data} size={32} />
      <WinConditionBlock data={data} limit={110} />
      <div style={{ display: 'flex', gap: 40, width: '100%' }}>
        <div style={{ display: 'flex', flex: 1 }}>
          <ItemRow title={data.labels.counters} items={data.counterItems} color={OG.gold} iconSize={78} />
        </div>
        <div style={{ display: 'flex', flex: 1 }}>
          <KillOrder data={data} compact />
        </div>
      </div>
      <AvoidBlock data={data} />
      <div style={{ display: 'flex', flex: 1 }} />
      <Footer data={data} big />
    </div>
  );
}

/** 1080×1080 — Instagram/Twitter feed post. */
export function renderSquare(data: PosterData) {
  return (
    <div style={{ ...frame, gap: 20, padding: 46 }}>
      <BrandBar labels={data.labels} />
      <HeroBand data={data} height={310} big={false} />
      <WinPlanBlock data={data} size={26} />
      <div style={{ display: 'flex', gap: 40, width: '100%' }}>
        <div style={{ display: 'flex', flex: 1 }}>
          <ItemRow title={data.labels.counters} items={data.counterItems} color={OG.gold} iconSize={68} />
        </div>
        <div style={{ display: 'flex', flex: 1 }}>
          <KillOrder data={data} compact />
        </div>
      </div>
      <div style={{ display: 'flex', flex: 1 }} />
      <Footer data={data} big={false} />
    </div>
  );
}

/** 1080×1350 — Instagram portrait / link card fallback. */
export function renderPortrait(data: PosterData) {
  return (
    <div style={{ ...frame, gap: 22 }}>
      <BrandBar labels={data.labels} />
      <HeroBand data={data} height={360} big={false} />
      <WinPlanBlock data={data} size={29} />
      <div style={{ display: 'flex', gap: 40, width: '100%' }}>
        <div style={{ display: 'flex', flex: 1 }}>
          <ItemRow title={data.labels.counters} items={data.counterItems} color={OG.gold} iconSize={72} />
        </div>
        <div style={{ display: 'flex', flex: 1 }}>
          <KillOrder data={data} compact />
        </div>
      </div>
      <AvoidBlock data={data} />
      <div style={{ display: 'flex', flex: 1 }} />
      <Footer data={data} big={false} />
    </div>
  );
}

export const POSTER_FORMATS = {
  story: { width: 1080, height: 1920, render: renderStory },
  square: { width: 1080, height: 1080, render: renderSquare },
  portrait: { width: 1080, height: 1350, render: renderPortrait },
} as const;

export type PosterFormat = keyof typeof POSTER_FORMATS;
