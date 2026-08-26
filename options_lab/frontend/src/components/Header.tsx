'use client';

import React, { useState } from 'react';
import { 
  Search, 
  Maximize, 
  Minimize, 
  Menu, 
  TrendingUp, 
  ChevronDown,
  User,
  Shield,
  LogOut,
  Sparkles
} from 'lucide-react';
import { useSidebar } from '@/components/Sidebar';
import { useAuth } from '@/context/AuthContext';
import { optionsApi } from '@/lib/api';

export default function Header() {
  const { toggleCollapse, setIsOpen } = useSidebar();
  const { user, logout } = useAuth();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [brokerEnv, setBrokerEnv] = useState<string>('LIVE');
  const [isLiveShield, setIsLiveShield] = useState<boolean>(true);

  React.useEffect(() => {
    optionsApi.getBrokerStatus().then((res) => {
      if (res?.environment) setBrokerEnv(res.environment);
      if (res?.allow_live_execution !== undefined) setIsLiveShield(!res.allow_live_execution);
    }).catch(() => {});
  }, []);


  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
        setIsFullscreen(false);
      }
    }
  };

  return (
    <header className="fixed top-0 right-0 left-0 h-16 bg-white border-b border-slate-200 z-40 flex items-center justify-between px-4 sm:px-6 transition-all duration-300">
      {/* Left section: Logo & Sidebar Toggle & Search */}
      <div className="flex items-center gap-3 sm:gap-4 flex-1">
        {/* Toggle Button for Mobile Drawer & Desktop Collapse */}
        <button
          onClick={() => {
            // Toggle desktop collapse or mobile drawer
            if (window.innerWidth < 1024) {
              setIsOpen(true);
            } else {
              toggleCollapse();
            }
          }}
          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition"
          aria-label="Toggle Navigation"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Brand Logo (Visible on Header for small screens) */}
        <div className="flex items-center gap-2 lg:hidden">
          <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white font-bold">
            <TrendingUp className="h-5 w-5" />
          </div>
          <span className="font-bold text-slate-800 tracking-tight text-lg">
            VELZON<span className="text-indigo-600 text-xs ml-1 font-semibold">QUANT</span>
          </span>
        </div>

        {/* Global Search Bar */}
        <div className="hidden sm:flex items-center relative max-w-xs w-full">
          <Search className="h-4 w-4 absolute left-3 text-slate-400 pointer-events-none" />
          <input
            type="text"
            placeholder="Search symbols, strategy rules, or endpoints..."
            className="w-full pl-9 pr-4 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 placeholder-slate-400 focus:bg-white focus:border-indigo-500 focus:outline-none transition"
          />
        </div>
      </div>

      {/* Right Section: Badges, Actions, User Pill */}
      <div className="flex items-center gap-2 sm:gap-4">
        {/* Environment Badge */}
        <span className="hidden md:inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold border bg-emerald-50 text-emerald-700 border-emerald-200 shadow-2xs">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          {brokerEnv === 'LIVE' ? 'Saxo LIVE (Trading Active)' : 'Saxo SIM Connected'}
        </span>

        {/* Fullscreen Button */}
        <button
          onClick={toggleFullscreen}
          className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition hidden sm:block"
          title="Toggle Fullscreen"
        >
          {isFullscreen ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
        </button>

        {/* User Profile Pill ("Sathish - Online") */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2.5 p-1.5 rounded-xl hover:bg-slate-100 transition border border-transparent hover:border-slate-200"
          >
            <div className="relative">
              <div className="h-9 w-9 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-indigo-700 font-bold text-sm">
                {user?.displayName ? user.displayName.charAt(0).toUpperCase() : 'S'}
              </div>
              <span className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-white" />
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-xs font-bold text-slate-800 leading-tight">
                {user?.displayName || 'Sathish'}
              </div>
              <div className="text-[11px] font-medium text-emerald-600 flex items-center gap-1">
                Online
              </div>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400 hidden sm:block" />
          </button>

          {/* User Dropdown */}
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 rounded-xl bg-white border border-slate-200 shadow-lg py-1.5 z-50 text-xs">
              <div className="px-4 py-2 border-b border-slate-100">
                <p className="font-bold text-slate-800">{user?.displayName || 'Sathish'}</p>
                <p className="text-[11px] text-slate-400 truncate">{user?.email || 'sathish84@gmail.com'}</p>
              </div>
              <a href="/portfolio" className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition">
                <User className="h-3.5 w-3.5" /> Profile & Account
              </a>
              <a href="/market-agents" className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition">
                <Shield className="h-3.5 w-3.5" /> Risk Controls
              </a>
              <div className="border-t border-slate-100 my-1" />
              <button
                onClick={async () => {
                  setShowUserMenu(false);
                  try {
                    await optionsApi.disconnectBroker();
                  } catch (e) {
                    console.error("Failed to disconnect broker:", e);
                  }
                  await logout();
                  if (typeof window !== 'undefined') {
                    window.location.href = '/';
                  }
                }}
                className="w-full text-left flex items-center gap-2 px-4 py-2 text-rose-600 hover:bg-rose-50 transition font-medium"
              >
                <LogOut className="h-3.5 w-3.5" /> Sign Out (Disconnect Bot)
              </button>
            </div>
          )}

        </div>
      </div>
    </header>
  );
}

