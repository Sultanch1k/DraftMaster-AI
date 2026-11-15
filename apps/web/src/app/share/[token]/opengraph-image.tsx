import { ImageResponse } from 'next/og';
import { decodeDraft } from '@/lib/share';
import { heroIcon, heroName } from '@/lib/heroes';

export const runtime = 'nodejs';
export const contentType = 'image/png';
export const size = { width: 1200, height: 630 };

const CDN = 'https://cdn.cloudflare.steamstatic.com';
const ACCENT = '#38e07b';
const DIREC = '#ff4d4d';

function iconUrl(id: number): string | null {
  const path = heroIcon(id);
  return path ? `${CDN}${path.split('?')[0]}` : null;
}

/**
 * Open Graph card for a shared win plan.
 *
 * This is the hook that makes a share worth clicking: a stranger scrolling
 * Reddit or Discord sees the enemy draft, the recommended pick and the win
 * probability rendered as a real card, not a bare link. It is generated on
 * demand from the same data the share page uses, so it can never disagree with
 * the plan it advertises.
 */
export default async function Image({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const draft = decodeDraft(token);
  const enemies = (draft?.e ?? []).map((id) => ({ id, name: heroName(id) ?? '?', icon: iconUrl(id) }));
  const pick = draft?.h ? { name: heroName(draft.h) ?? '?', icon: iconUrl(draft.h) } : null;
  const win = draft?.w;

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: 'linear-gradient(135deg, #07090d 0%, #0f141d 55%, #141a25 100%)',
          padding: 64,
          fontFamily: 'sans-serif',
          color: '#e2e8f0',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div
              style={{
                width: 56,
                height: 56,
                borderRadius: 14,
                background: `linear-gradient(135deg, ${ACCENT}, #1f8f4d)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 32,
              }}
            >
              🛡️
            </div>
            <div style={{ display: 'flex', fontSize: 34, fontWeight: 800, letterSpacing: -1 }}>
              DraftMaster<span style={{ color: ACCENT }}>&nbsp;AI</span>
            </div>
          </div>
          <div style={{ display: 'flex', fontSize: 24, color: '#7c8aa0' }}>draftmaster.wiki</div>
        </div>

        <div style={{ display: 'flex', marginTop: 44, fontSize: 30, color: '#94a3b8' }}>ENEMY DRAFT</div>
        <div style={{ display: 'flex', gap: 20, marginTop: 16 }}>
          {enemies.map((h) => (
            <div key={h.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 150 }}>
              <div
                style={{
                  width: 150,
                  height: 150,
                  borderRadius: 18,
                  border: `3px solid ${DIREC}66`,
                  background: '#1c2431',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                  fontSize: 44,
                  fontWeight: 800,
                  color: '#64748b',
                }}
              >
                {h.icon ? <img src={h.icon} width={150} height={150} alt="" /> : h.name[0]}
              </div>
              <div style={{ display: 'flex', marginTop: 10, fontSize: 22, color: '#cbd5e1' }}>{h.name}</div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', flex: 1, alignItems: 'flex-end', justifyContent: 'space-between' }}>
          {pick && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
              <div
                style={{
                  width: 190,
                  height: 190,
                  borderRadius: 22,
                  border: `4px solid ${ACCENT}`,
                  background: '#1c2431',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  overflow: 'hidden',
                }}
              >
                {pick.icon ? <img src={pick.icon} width={190} height={190} alt="" /> : pick.name[0]}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ display: 'flex', fontSize: 26, color: ACCENT, fontWeight: 700 }}>#1 BEST PICK</div>
                <div style={{ display: 'flex', fontSize: 72, fontWeight: 900, color: '#ffffff', letterSpacing: -2 }}>
                  {pick.name}
                </div>
                <div style={{ display: 'flex', fontSize: 26, color: '#94a3b8' }}>the full win plan in 5 seconds</div>
              </div>
            </div>
          )}
          {typeof win === 'number' && (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
              <div style={{ display: 'flex', fontSize: 26, color: '#94a3b8' }}>DRAFT WIN PROBABILITY</div>
              <div style={{ display: 'flex', fontSize: 110, fontWeight: 900, color: ACCENT, letterSpacing: -3 }}>
                {win}%
              </div>
            </div>
          )}
        </div>
      </div>
    ),
    { ...size },
  );
}
