'use client';

import React from 'react';
import { LucideIcon, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface MetricCardProps {
  title: string;
  value: string;
  subtext: string;
  change: string;
  isPositive?: boolean;
  badgeText?: string;
  icon: LucideIcon;
  iconBgColor: string;
  iconTextColor: string;
  iconBorderColor: string;
}

export default function MetricCard({
  title,
  value,
  subtext,
  change,
  isPositive = true,
  badgeText,
  icon: Icon,
  iconBgColor,
  iconTextColor,
  iconBorderColor,
}: MetricCardProps) {
  return (
    <div className="velzon-card p-5 relative overflow-hidden group">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{title}</span>
        {badgeText ? (
          <span className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-bold badge-soft-primary">
            {badgeText}
          </span>
        ) : (
          <span
            className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-[11px] font-bold ${
              isPositive ? 'badge-soft-success' : 'badge-soft-danger'
            }`}
          >
            {isPositive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
            {change}
          </span>
        )}
      </div>

      <div className="mt-3 flex items-baseline justify-between">
        <div>
          <h3 className="text-2xl font-extrabold text-slate-800 tracking-tight">{value}</h3>
          <p className="text-[11px] text-slate-400 mt-1">{subtext}</p>
        </div>
        <div
          className={`h-11 w-11 rounded-xl ${iconBgColor} ${iconTextColor} flex items-center justify-center border ${iconBorderColor} group-hover:scale-110 transition-transform`}
        >
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}
