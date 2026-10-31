import React from "react";
import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { cn, formatCurrency } from "../../lib/utils";

export function StatCard({
  title,
  value,
  isCurrency = false,
  currency = "USD",
  icon: Icon,
  trend,
  trendLabel = "vs last period",
  subtext,
  isLoading = false,
  badgeText,
  badgeVariant = "brand",
  accentColor = "text-brand-400 bg-brand-500/10 border-brand-500/20",
}) {
  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-5 animate-pulse">
        <div className="flex items-center justify-between pb-3">
          <div className="h-4 w-24 bg-slate-800 rounded"></div>
          <div className="h-8 w-8 bg-slate-800 rounded-lg"></div>
        </div>
        <div className="h-7 w-32 bg-slate-800 rounded my-2"></div>
        <div className="h-3 w-20 bg-slate-800 rounded mt-2"></div>
      </div>
    );
  }

  const displayValue = isCurrency ? formatCurrency(value, currency) : (value ?? 0);

  return (
    <div className="rounded-xl border border-slate-800/80 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm transition-all duration-200 hover:border-slate-700/80 hover:bg-slate-900/90 hover:shadow-xl">
      <div className="flex items-center justify-between pb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className={cn("p-2 rounded-lg border", accentColor)}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="mt-1 flex items-baseline justify-between gap-2">
        <div className="text-2xl font-bold tracking-tight text-white">
          {displayValue}
        </div>
        {badgeText && (
          <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-slate-800 text-slate-300 border border-slate-700">
            {badgeText}
          </span>
        )}
      </div>

      {(trend !== undefined || subtext) && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-400">
          {trend !== undefined && (
            <span
              className={cn(
                "inline-flex items-center font-medium",
                trend >= 0 ? "text-emerald-400" : "text-rose-400"
              )}
            >
              {trend >= 0 ? (
                <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" />
              ) : (
                <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />
              )}
              {Math.abs(trend)}%
            </span>
          )}
          <span>{subtext || trendLabel}</span>
        </div>
      )}
    </div>
  );
}

export default StatCard;
