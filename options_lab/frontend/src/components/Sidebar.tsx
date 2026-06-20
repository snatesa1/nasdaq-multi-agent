'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { 
  TrendingUp, 
  Percent, 
  Layers, 
  BookOpen, 
  Briefcase, 
  Bot,
  Cpu,
  LogOut
} from 'lucide-react';

const navItems = [
  { name: 'Dashboard', path: '/', icon: Cpu },
  { name: 'GBM Playground', path: '/simulator', icon: TrendingUp },
  { name: 'Option Pricer', path: '/pricer', icon: Percent },
  { name: 'Strategy Builder', path: '/strategies', icon: Layers },
  { name: 'Paper Trading', path: '/paper-trade', icon: Briefcase },
  { name: 'Socratic Tutor', path: '/learn', icon: BookOpen },
  { name: 'Portfolio', path: '/portfolio', icon: Briefcase },
  { name: 'Market Agents', path: '/market-agents', icon: Bot },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="fixed inset-y-0 left-0 z-20 flex w-64 flex-col border-r border-slate-800 bg-[#161924]/80 backdrop-blur-md">
      <div className="flex h-16 items-center px-6 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg text-slate-100">
          <TrendingUp className="h-6 w-6 text-[#5ba4b5]" />
          <span>Options<span className="text-[#5ba4b5]">Lab</span></span>
        </Link>
      </div>
      
      <nav className="flex-1 space-y-1 px-4 py-6">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.path}
              className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive 
                  ? 'bg-[#5ba4b5]/10 text-[#5ba4b5] border-l-2 border-[#5ba4b5] pl-3' 
                  : 'text-slate-400 hover:bg-[#1a1d28] hover:text-slate-200'
              }`}
            >
              <Icon className={`h-5 w-5 ${isActive ? 'text-[#5ba4b5]' : 'text-slate-400 group-hover:text-slate-300'}`} />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>
      
      <div className="p-4 border-t border-slate-800 bg-[#12141c]/50">
        {user ? (
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              {user.photoURL ? (
                <img 
                  src={user.photoURL} 
                  alt={user.displayName || 'User'} 
                  className="h-9 w-9 rounded-full border border-slate-700"
                />
              ) : (
                <div className="h-9 w-9 rounded-full bg-[#5ba4b5]/20 flex items-center justify-center text-xs font-bold text-[#5ba4b5]">
                  {user.displayName?.charAt(0)?.toUpperCase() || user.email?.charAt(0)?.toUpperCase() || 'U'}
                </div>
              )}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user.displayName || 'User'}
                </p>
                <p className="text-[10px] text-slate-400 truncate">
                  {user.email || 'Authenticated'}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              className="w-full flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900/50 px-3 py-2 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:border-slate-600 transition"
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign Out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-full bg-[#5ba4b5]/20 flex items-center justify-center text-xs font-bold text-[#5ba4b5]">
              USER
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-200">Personal Sandbox</p>
              <p className="text-[10px] text-slate-400">Zero Capital Loss</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
