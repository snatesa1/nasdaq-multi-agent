'use client';

import React, { useState, useEffect, createContext, useContext } from 'react';
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
  LogOut,
  Calendar,
  Menu,
  X,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

// ── Sidebar Context ──────────────────────────────────────────────────────────
interface SidebarContextType {
  isOpen: boolean;
  isCollapsed: boolean;
  setIsOpen: (v: boolean) => void;
  toggleCollapse: () => void;
}

const SidebarContext = createContext<SidebarContextType>({
  isOpen: false,
  isCollapsed: false,
  setIsOpen: () => {},
  toggleCollapse: () => {},
});

export const useSidebar = () => useContext(SidebarContext);

// ── Nav Items ────────────────────────────────────────────────────────────────
const navItems = [
  { name: 'Dashboard', path: '/', icon: Cpu },
  { name: 'GBM Playground', path: '/simulator', icon: TrendingUp },
  { name: 'Option Pricer', path: '/pricer', icon: Percent },
  { name: 'Strategy Builder', path: '/strategies', icon: Layers },
  { name: 'Earnings Plays', path: '/earnings', icon: Calendar },
  { name: 'Paper Trading', path: '/paper-trade', icon: Briefcase },
  { name: 'Socratic Tutor', path: '/learn', icon: BookOpen },
  { name: 'Portfolio', path: '/portfolio', icon: Briefcase },
  { name: 'Market Agents', path: '/market-agents', icon: Bot },
];

// ── Sidebar Provider (wraps children with state) ─────────────────────────────
export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);       // mobile drawer
  const [isCollapsed, setIsCollapsed] = useState(false); // desktop collapse

  const toggleCollapse = () => setIsCollapsed(prev => !prev);

  return (
    <SidebarContext.Provider value={{ isOpen, isCollapsed, setIsOpen, toggleCollapse }}>
      {children}
    </SidebarContext.Provider>
  );
}

// ── Main Sidebar Component ───────────────────────────────────────────────────
export default function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const { isOpen, isCollapsed, setIsOpen, toggleCollapse } = useSidebar();

  // Close mobile drawer on route change
  useEffect(() => {
    setIsOpen(false);
  }, [pathname, setIsOpen]);

  // Close mobile drawer on Escape key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [setIsOpen]);

  const sidebarWidth = isCollapsed ? 'w-[72px]' : 'w-64';

  const sidebarContent = (
    <>
      {/* Logo Header */}
      <div className="flex h-16 items-center border-b border-slate-800 px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-lg text-slate-100 min-w-0">
          <TrendingUp className="h-6 w-6 text-[#5ba4b5] flex-shrink-0" />
          {!isCollapsed && (
            <span className="truncate">
              Options<span className="text-[#5ba4b5]">Lab</span>
            </span>
          )}
        </Link>
        {/* Desktop collapse toggle */}
        <button
          onClick={toggleCollapse}
          className="hidden lg:flex ml-auto p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
        {/* Mobile close */}
        <button
          onClick={() => setIsOpen(false)}
          className="lg:hidden ml-auto p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      
      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.path;
          const Icon = item.icon;
          return (
            <Link
              key={item.name}
              href={item.path}
              title={isCollapsed ? item.name : undefined}
              className={`flex items-center gap-3 rounded-lg text-sm font-medium transition-all duration-200 ${
                isCollapsed ? 'justify-center px-2 py-3' : 'px-4 py-3'
              } ${
                isActive 
                  ? 'bg-[#5ba4b5]/10 text-[#5ba4b5] border-l-2 border-[#5ba4b5]' 
                  : 'text-slate-400 hover:bg-[#1a1d28] hover:text-slate-200'
              }`}
            >
              <Icon className={`h-5 w-5 flex-shrink-0 ${isActive ? 'text-[#5ba4b5]' : 'text-slate-400'}`} />
              {!isCollapsed && <span className="truncate">{item.name}</span>}
            </Link>
          );
        })}
      </nav>
      
      {/* User Footer */}
      <div className="border-t border-slate-800 bg-[#12141c]/50">
        {user ? (
          <div className={`p-3 ${isCollapsed ? 'flex flex-col items-center gap-2' : 'space-y-3'}`}>
            <div className={`flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
              {user.photoURL ? (
                <img 
                  src={user.photoURL} 
                  alt={user.displayName || 'User'} 
                  className="h-9 w-9 rounded-full border border-slate-700 flex-shrink-0"
                />
              ) : (
                <div className="h-9 w-9 rounded-full bg-[#5ba4b5]/20 flex items-center justify-center text-xs font-bold text-[#5ba4b5] flex-shrink-0">
                  {user.displayName?.charAt(0)?.toUpperCase() || user.email?.charAt(0)?.toUpperCase() || 'U'}
                </div>
              )}
              {!isCollapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-slate-200 truncate">
                    {user.displayName || 'User'}
                  </p>
                  <p className="text-[10px] text-slate-400 truncate">
                    {user.email || 'Authenticated'}
                  </p>
                </div>
              )}
            </div>
            <button
              onClick={logout}
              title={isCollapsed ? 'Sign Out' : undefined}
              className={`flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-900/50 text-xs font-semibold text-slate-400 hover:text-slate-200 hover:border-slate-600 transition ${
                isCollapsed ? 'p-2 w-full' : 'w-full px-3 py-2'
              }`}
            >
              <LogOut className="h-3.5 w-3.5 flex-shrink-0" />
              {!isCollapsed && <span>Sign Out</span>}
            </button>
          </div>
        ) : (
          <div className={`p-3 flex items-center ${isCollapsed ? 'justify-center' : 'gap-3'}`}>
            <div className="h-9 w-9 rounded-full bg-[#5ba4b5]/20 flex items-center justify-center text-xs font-bold text-[#5ba4b5] flex-shrink-0">
              U
            </div>
            {!isCollapsed && (
              <div>
                <p className="text-xs font-semibold text-slate-200">Personal Sandbox</p>
                <p className="text-[10px] text-slate-400">Zero Capital Loss</p>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );

  return (
    <>
      {/* ── Mobile Top Bar ──────────────────────────────────────────────────── */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-30 h-14 flex items-center gap-3 px-4 border-b border-slate-800 bg-[#161924]/95 backdrop-blur-md">
        <button
          onClick={() => setIsOpen(true)}
          className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          aria-label="Open navigation menu"
        >
          <Menu className="h-5 w-5" />
        </button>
        <Link href="/" className="flex items-center gap-2 font-bold text-lg text-slate-100">
          <TrendingUp className="h-5 w-5 text-[#5ba4b5]" />
          Options<span className="text-[#5ba4b5]">Lab</span>
        </Link>
      </div>

      {/* ── Mobile Overlay ──────────────────────────────────────────────────── */}
      {isOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm transition-opacity"
          onClick={() => setIsOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ── Mobile Drawer ───────────────────────────────────────────────────── */}
      <aside
        className={`lg:hidden fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-800 bg-[#161924] transform transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {sidebarContent}
      </aside>

      {/* ── Desktop Sidebar ─────────────────────────────────────────────────── */}
      <aside
        className={`hidden lg:flex fixed inset-y-0 left-0 z-20 flex-col border-r border-slate-800 bg-[#161924]/80 backdrop-blur-md transition-all duration-300 ease-in-out ${sidebarWidth}`}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
