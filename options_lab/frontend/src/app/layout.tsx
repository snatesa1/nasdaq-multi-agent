import './globals.css';
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import Sidebar from '@/components/Sidebar';
import { AuthProvider } from '@/context/AuthContext';

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
      <body className={`${inter.className} bg-[#12141a] text-slate-100 min-h-screen antialiased`}>
        <AuthProvider>
          <div className="flex">
            <Sidebar />
            <main className="flex-1 min-h-screen ml-64 p-8">
              <div className="mx-auto max-w-7xl">
                {children}
              </div>
            </main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

