import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

/**
 * Fonts for the server-rendered social poster and OG cards.
 *
 * Vendored as static files under `src/assets/fonts` so rendering never depends
 * on a network fetch at request time (a slow or blocked font host would
 * otherwise produce a broken poster). Satori needs the raw bytes; these are
 * loaded once per server process.
 */
export type OgFont = { name: string; data: Buffer; weight: 400 | 700 | 900; style: 'normal' };

let cache: OgFont[] | null = null;

export async function loadOgFonts(): Promise<OgFont[]> {
  if (cache) return cache;
  const dir = join(process.cwd(), 'src', 'assets', 'fonts');
  const [inter400, inter700, playfair700, playfair900] = await Promise.all([
    readFile(join(dir, 'inter-400.woff')),
    readFile(join(dir, 'inter-700.woff')),
    readFile(join(dir, 'playfair-700.woff')),
    readFile(join(dir, 'playfair-900.woff')),
  ]);
  cache = [
    { name: 'Inter', data: inter400, weight: 400, style: 'normal' },
    { name: 'Inter', data: inter700, weight: 700, style: 'normal' },
    { name: 'Playfair Display', data: playfair700, weight: 700, style: 'normal' },
    { name: 'Playfair Display', data: playfair900, weight: 900, style: 'normal' },
  ];
  return cache;
}

/** Shared brand tokens for image rendering (Satori cannot read Tailwind classes). */
export const OG = {
  bg: '#090B10',
  surface: '#11151D',
  elevated: '#171D27',
  border: '#232B38',
  ink: '#F2F0EA',
  inkSoft: '#D7D9DE',
  muted: '#A4ACB9',
  faint: '#6B7484',
  accent: '#C8362F',
  accentBright: '#E5484D',
  radiant: '#4FB477',
  dire: '#D9484D',
  gold: '#C9A24B',
  steel: '#6B7A8F',
} as const;
