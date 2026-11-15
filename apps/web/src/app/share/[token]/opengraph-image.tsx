import { ImageResponse } from 'next/og';
import { decodeDraft } from '@/lib/share';
import { heroIcon, heroName } from '@/lib/heroes';
import { cdn } from '@/lib/format';
import { loadOgFonts, OG } from '@/lib/og-fonts';

export const runtime = 'nodejs';
export const contentType = 'image/png';
export const size = { width: 1200, height: 630 };

/**
 * Open Graph card for a shared win plan.
 *
 * This is the hook that makes a share worth clicking: a stranger scrolling
 * Reddit or Discord sees the enemy draft, the recommended pick and the
 * heuristic draft-edge score rendered as a real card, not a bare link. It is generated on
 * demand from the same signed payload the share page uses, so it can never
 * advertise a different plan than the one it links to.
 */
export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const draft = decodeDraft(token);
  const enemies = (draft?.e ?? []).map((id) => {
    const icon = heroIcon(id);
    return { id, name: heroName(id) ?? '?', icon: icon ? cdn(icon) : null };
  });
  const pickIcon = draft?.h ? heroIcon(draft.h) : null;
  const pick = draft?.h
    ? { name: heroName(draft.h) ?? '?', icon: pickIcon ? cdn(pickIcon) : null }
    : null;
  const win = draft?.w;
  const fonts = await loadOgFonts();

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: `linear-gradient(135deg, ${OG.bg} 0%, ${OG.surface} 55%, ${OG.elevated} 100%)`,
          padding: 60,
          fontFamily: 'Inter',
          color: OG.ink,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div
              style={{
                width: 54,
                height: 54,
                borderRadius: 14,
                background: `linear-gradient(135deg, ${OG.accent}, ${OG.accentBright})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 30,
                fontWeight: 900,
                color: '#FFFFFF',
              }}
            >
              D
            </div>
            <div style={{ display: 'flex', fontSize: 32, fontWeight: 700, letterSpacing: -0.5 }}>
              DraftMaster&nbsp;<span style={{ color: OG.accentBright }}>AI</span>
            </div>
          </div>
          <div style={{ display: 'flex', fontSize: 24, color: OG.faint }}>draftmaster.wiki</div>
        </div>

        <div style={{ display: 'flex', marginTop: 40, fontSize: 26, letterSpacing: 3, color: OG.muted }}>
          ENEMY DRAFT
        </div>
        <div style={{ display: 'flex', gap: 18, marginTop: 14 }}>
          {enemies.map((h) => (
            <div key={h.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 140 }}>
              <div
                style={{
                  width: 140,
                  height: 140,
                  borderRadius: 16,
                  border: `2px solid ${OG.dire}66`,
                  background: OG.elevated,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  fontSize: 44,
                  fontWeight: 800,
                  color: OG.faint,
                }}
              >
                {h.icon ? <img src={h.icon} width={140} height={140} alt="" /> : h.name[0]}
              </div>
              <div style={{ display: 'flex', marginTop: 8, fontSize: 20, color: OG.inkSoft }}>{h.name}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', flex: 1, alignItems: 'flex-end', justifyContent: 'space-between' }}>
          {pick && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <div
                style={{
                  width: 176,
                  height: 176,
                  borderRadius: 20,
                  border: `3px solid ${OG.accentBright}`,
                  background: OG.elevated,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                }}
              >
                {pick.icon ? <img src={pick.icon} width={176} height={176} alt="" /> : pick.name[0]}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', fontSize: 24, color: OG.accentBright, fontWeight: 700, letterSpacing: 2 }}>
                  #1 BEST PICK
                </div>
                <div
                  style={{
                    display: 'flex',
                    fontSize: 76,
                    fontWeight: 900,
                    color: '#FFFFFF',
                    letterSpacing: -2,
                    fontFamily: 'Playfair Display',
                  }}
                >
                  {pick.name}
                </div>
                <div style={{ display: 'flex', fontSize: 24, color: OG.muted }}>the full win plan in 5 seconds</div>
              </div>
            </div>
          )}
          {typeof win === 'number' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <div style={{ display: 'flex', fontSize: 24, color: OG.muted, letterSpacing: 1 }}>
                DRAFT-EDGE SCORE
              </div>
              <div
                style={{
                  display: 'flex',
                  fontSize: 108,
                  fontWeight: 900,
                  color: OG.accentBright,
                  letterSpacing: -3,
                  fontFamily: 'Playfair Display',
                }}
              >
                {win}/100
              </div>
            </div>
          )}
        </div>
      </div>
    ),
    { ...size, fonts },
  );
}
