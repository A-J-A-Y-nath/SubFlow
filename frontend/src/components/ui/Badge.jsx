import React from "react";
import { cn, getStatusColor } from "../../lib/utils";

export function Badge({ children, variant, status, className }) {
  let colorClass = "bg-slate-800 text-slate-300 border-slate-700";

  if (status) {
    colorClass = getStatusColor(status);
  } else if (variant === "brand") {
    colorClass = "bg-brand-500/15 text-brand-300 border-brand-500/30";
  } else if (variant === "success") {
    colorClass = "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
  } else if (variant === "danger") {
    colorClass = "bg-rose-500/15 text-rose-300 border-rose-500/30";
  } else if (variant === "warning") {
    colorClass = "bg-amber-500/15 text-amber-300 border-amber-500/30";
  }

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border uppercase tracking-wider",
        colorClass,
        className
      )}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70"></span>
      {children}
    </span>
  );
}

export default Badge;
