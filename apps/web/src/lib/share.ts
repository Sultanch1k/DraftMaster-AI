/**
 * Share link decoding.
 *
 * A share link is a *server-signed* token of the form `payload.signature`. The
 * signature is what makes the public render endpoint safe: only a quota-paying
 * analysis can mint a token, so a stranger opening a shared plan is spending the
 * sharer's quota rather than getting free unlimited access.
 *
 * The client only needs to *decode* the token (for the page title and the OG
 * image); it never creates one — that is `POST /api/share`, which charges quota.
 */
export type DraftPayload = {
  /** Enemy hero ids, in selection order. */
  e: number[];
  /** The recommended hero id. */
  h?: number;
  /** Draft win probability, as a whole percent. */
  w?: number;
  /** Role the plan was generated for. */
  r?: string;
  /** Rank tier. */
  rk?: number;
};

function fromBase64Url(token: string): string {
  const b64 = token.replace(/-/g, '+').replace(/_/g, '/');
  const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4);
  return typeof atob === 'function' ? atob(padded) : Buffer.from(padded, 'base64').toString('binary');
}

/**
 * Decode a signed share token into its payload, or null if it is malformed.
 * Signature verification happens server-side; this is only for rendering.
 */
export function decodeDraft(token: string): DraftPayload | null {
  try {
    const [body] = token.split('.');
    if (!body) return null;
    const wrapper = JSON.parse(fromBase64Url(body)) as { p?: DraftPayload };
    const parsed = wrapper?.p;
    if (!parsed || !Array.isArray(parsed.e) || parsed.e.length === 0 || parsed.e.length > 5) return null;
    const e = parsed.e.map((n) => Number(n)).filter((n) => Number.isInteger(n) && n > 0);
    if (e.length === 0) return null;
    return {
      e,
      h: parsed.h ? Number(parsed.h) : undefined,
      w: parsed.w ? Number(parsed.w) : undefined,
      r: parsed.r,
      rk: parsed.rk ? Number(parsed.rk) : undefined,
    };
  } catch {
    return null;
  }
}
