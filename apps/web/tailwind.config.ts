import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: 'class',
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dota-inspired dark palette: deep slate surfaces, radiant green + dire red accents.
        base: {
          950: '#07090d',
          900: '#0b0f16',
          850: '#0f141d',
          800: '#141a25',
          700: '#1c2431',
          600: '#27313f',
        },
        radiant: { DEFAULT: '#38e07b', dim: '#1f8f4d' },
        dire: { DEFAULT: '#ff4d4d', dim: '#a32a2a' },
        gold: { DEFAULT: '#f2c14e', dim: '#b98f26' },
        magic: { DEFAULT: '#7c5cff' },
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glow: '0 0 24px -6px rgba(56,224,123,0.55)',
        'glow-red': '0 0 24px -6px rgba(255,77,77,0.55)',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(6px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        pulseRing: { '0%': { transform: 'scale(0.9)', opacity: '0.7' }, '100%': { transform: 'scale(1.4)', opacity: '0' } },
      },
      animation: {
        'fade-up': 'fade-up 0.35s ease-out both',
        'pulse-ring': 'pulseRing 1.4s ease-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
