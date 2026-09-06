import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import { AuthProvider } from '@/context/AuthContext';
import ClientLayout from '@/components/ClientLayout';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'OptionsLab — Socratic Simulator',
  description: 'Interactive options strategy sandbox and Socratic learning environment.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta
          httpEquiv="Content-Security-Policy"
          content="default-src 'self' 'unsafe-inline' 'unsafe-eval' http: https: data: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https:; style-src 'self' 'unsafe-inline' https: fonts.googleapis.com; font-src 'self' data: https: fonts.gstatic.com; img-src 'self' data: blob: https:; connect-src 'self' http: https: ws: wss:; frame-src 'self' https:;"
        />
      </head>
      <body className={`${inter.className} bg-[#F3F3F9] text-slate-800 min-h-screen antialiased`}>
        <AuthProvider>
          <ClientLayout>
            {children}
          </ClientLayout>
        </AuthProvider>
      </body>
    </html>
  );
}

