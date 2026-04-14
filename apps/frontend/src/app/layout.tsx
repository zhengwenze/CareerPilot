import type { Metadata } from 'next';

import { AuthProvider } from '@/components/auth-provider';

import './globals.css';

export const metadata: Metadata = {
  title: 'CareerPilot',
  description: 'AI 求职导航台入口',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
