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
  ChevronRight,
  Shield,
  Award,
  Sparkles,
  DollarSign,
  Compass
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

// ── Nav Groups (Velzon Structured Taxonomy) ───────────────────────────
const navGroups = [
  {
    title: 'DASHBOARDS',
    items: [
      { name: 'Analytics Overview', path: '/', icon: Cpu },
      { name: 'Portfolio Summary', path: '/portfolio', icon: Briefcase },
    ]
  },
  {
    title: 'SAXO QUANT LAB',
    items: [
      { name: 'Strategy Builder', path: '/strategies', icon: Layers, badge: 'Hot', badgeColor: 'bg-rose-100 text-rose-700' },
      { name: 'Option Pricer', path: '/pricer', icon: Percent },
      { name: 'Behavioral Forensics', path: '/behavioral-lab', icon: Compass, badge: 'New', badgeColor: 'bg-indigo-100 text-indigo-700' },
    ]
  },

  {
    title: 'MARKET SCANNER',
    items: [
      { name: 'Earnings Plays', path: '/earnings', icon: Calendar, badge: 'Live', badgeColor: 'bg-emerald-100 text-emerald-700' },
      { name: 'Market Agents', path: '/market-agents', icon: Bot },
    ]
  },
  {
    title: 'ACADEMIC & LEARNING',
    items: [
      { name: 'Socratic Tutor', path: '/learn', icon: BookOpen, badge: 'AI', badgeColor: 'bg-indigo-100 text-indigo-700' },
      { name: 'What-If Scenarios', path: '/paper-trade', icon: Award },
    ]
  }
];

// ── Sidebar Provider (wraps children with state) ─────────────────────────────
export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);         // mobile drawer
  const [isCollapsed, setIsCollapsed] = useState(false);   // desktop collapse

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
    <div className="flex flex-col h-full bg-white border-r border-slate-200 shadow-sm">
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-100 px-4">
        <Link href="/" className="flex items-center gap-2.5 min-w-0">
          <div className="h-9 w-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-200 flex-shrink-0">
            <TrendingUp className="h-5 w-5" />
          </div>
          {!isCollapsed && (
            <div className="flex flex-col min-w-0">
              <span className="font-extrabold text-slate-800 tracking-tight text-base leading-tight truncate">
                OPTIONS<span className="text-indigo-600">LAB</span>
              </span>
              <span className="text-[10px] font-bold tracking-widest uppercase text-slate-400">
                VELZON QUANT
              </span>
            </div>
          )}
        </Link>

        {/* Desktop collapse icon toggle */}
        <button
          onClick={toggleCollapse}
          className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>

        {/* Mobile close button */}
        <button
          onClick={() => setIsOpen(false)}
          className="lg:hidden p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Navigation Group Links */}
      <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
        {navGroups.map((group, gIdx) => (
          <div key={gIdx} className="space-y-1">
            {!isCollapsed && (
              <h3 className="px-3 text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-2">
                {group.title}
              </h3>
            )}
            {group.items.map((item) => {
              const isActive = pathname === item.path;
              const Icon = item.icon;

              return (
                <Link
                  key={item.path}
                  href={item.path}
                  title={isCollapsed ? item.name : undefined}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-200 group ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 shadow-sm border border-indigo-100/60 font-bold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <Icon
                    className={`h-4 w-4 flex-shrink-0 transition-colors ${
                      isActive ? 'text-indigo-600' : 'text-slate-400 group-hover:text-slate-600'
                    }`}
                  />
                  {!isCollapsed && (
                    <div className="flex items-center justify-between flex-1 min-w-0">
                      <span className="truncate">{item.name}</span>
                      {item.badge && (
                        <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${item.badgeColor}`}>
                          {item.badge}
                        </span>
                      )}
                    </div>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      {/* Pro Banner Footer (Only shown when expanded) */}
      {!isCollapsed && (
        <div className="p-3 m-3 rounded-xl bg-gradient-to-br from-indigo-50 to-blue-50 border border-indigo-100 text-center space-y-2">
          <div className="inline-flex h-8 w-8 rounded-full bg-indigo-600 text-white items-center justify-center shadow-md shadow-indigo-200">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800">Saxo Live Platform</h4>
            <p className="text-[11px] text-slate-500">Safety Shield Active</p>
          </div>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Desktop Sidebar (Fixed) */}
      <aside
        className={`hidden lg:block fixed top-0 left-0 bottom-0 z-30 transition-all duration-300 ease-in-out ${sidebarWidth}`}
      >
        {sidebarContent}
      </aside>

      {/* Mobile Sidebar (Slide-out Drawer) */}
      {isOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          {/* Backdrop Overlay */}
          <div
            className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
            onClick={() => setIsOpen(false)}
          />
          {/* Drawer Panel */}
          <div className="relative w-64 max-w-[80vw] bg-white h-full shadow-2xl z-10 animate-in slide-in-from-left duration-300">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
