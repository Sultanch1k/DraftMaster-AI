import type { Metadata, Viewport } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'DraftMaster AI — Here is exactly how to win this specific game',
  description:
    'DraftMaster AI is the Dota 2 AI coach that turns the enemy draft into a complete win plan: best picks, dynamic item build, threat analysis, win conditions, kill priority and a WIN PROBABILITY ENGINE.',
  applicationName: 'DraftMaster AI',
  openGraph: {
    title: 'DraftMaster AI',
    description: 'One Click Win Plan for Dota 2. Counter picks, dynamic items, win conditions.',
    type: 'website',
  },
};

export const viewport: Viewport = {
  themeColor: '#07090d',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-dvh font-sans antialiased">{children}</body>
    </html>
  );
}
