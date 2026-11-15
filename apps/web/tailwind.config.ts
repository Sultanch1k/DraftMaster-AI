import type { Config } from 'tailwindcss';

/**
 * DraftMaster design tokens.
 *
 * Two intentional systems, one palette:
 *  - Hero Identity: cinematic portraits on near-black charcoal with warm off-white
 *    editorial type. The hero is the protagonist of the dossier.
 *  - Tactical Editorial: dense, structured strategy (numbered kill order, item
 *    progression, phase timeline) on elevated surfaces with hairline rules.
 *
 * The old `base/radiant/dire/gold/magic` keys are kept (retuned, not renamed) so
 * every existing component inherits the new identity without a mass rewrite.
 */
const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Charcoal surfaces, darkest to most elevated.
        base: {
          950: '#090B10', // page background
          900: '#0E1117', // sunken wells
          850: '#11151D', // secondary background / cards
          800: '#171D27', // elevated surface
          700: '#232B38', // border / raised
          600: '#2E3746', // border strong
        },
        // Text ramp (warm off-white -> muted slate).
        ink: {
          DEFAULT: '#F2F0EA',
          soft: '#D7D9DE',
          muted: '#A4ACB9',
          faint: '#6B7484',
        },
        // Primary accent: controlled crimson / deep vermilion.
        accent: {
          DEFAULT: '#C8362F',
          bright: '#E5484D',
          dim: '#7E2620',
        },
        // Positive tactical indicator: muted green.
        radiant: { DEFAULT: '#4FB477', dim: '#2C6E4A' },
        // Danger indicator: controlled red (kept distinct from the crimson accent).
        dire: { DEFAULT: '#D9484D', dim: '#8A2A2E' },
        // Secondary accent: restrained antique gold.
        gold: { DEFAULT: '#C9A24B', dim: '#8C7031' },
        // Neutral information: muted blue-grey.
        steel: { DEFAULT: '#6B7A8F', dim: '#414C5E' },
        // Retained for existing usages.
        magic: { DEFAULT: '#7C5CFF' },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'Georgia', 'serif'],
        heading: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        panel: '14px',
        chip: '8px',
      },
      boxShadow: {
        glow: '0 0 24px -6px rgba(79,180,119,0.5)',
        'glow-red': '0 0 24px -6px rgba(217,72,77,0.5)',
        'glow-accent': '0 0 28px -8px rgba(200,54,47,0.6)',
        panel: '0 1px 0 0 rgba(255,255,255,0.03) inset, 0 18px 40px -28px rgba(0,0,0,0.9)',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(6px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        pulseRing: { '0%': { transform: 'scale(0.9)', opacity: '0.7' }, '100%': { transform: 'scale(1.4)', opacity: '0' } },
        sweep: { '0%': { backgroundPosition: '-120% 0' }, '100%': { backgroundPosition: '220% 0' } },
      },
      animation: {
        'fade-up': 'fade-up 0.35s ease-out both',
        'pulse-ring': 'pulseRing 1.4s ease-out infinite',
        sweep: 'sweep 2.4s linear infinite',
      },
    },
  },
  plugins: [],
};

export default config;
