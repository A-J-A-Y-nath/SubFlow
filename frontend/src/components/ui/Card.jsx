import React from "react";
import { cn } from "../../lib/utils";

export function Card({ className, children, hover = false, ...props }) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl backdrop-blur-sm",
        hover && "transition-all duration-200 hover:border-slate-700 hover:shadow-2xl hover:bg-slate-900/90",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ className, children, ...props }) {
  return (
    <div className={cn("flex flex-col space-y-1.5 pb-4", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ className, children, ...props }) {
  return (
    <h3 className={cn("text-lg font-semibold tracking-tight text-white", className)} {...props}>
      {children}
    </h3>
  );
}

export function CardDescription({ className, children, ...props }) {
  return (
    <p className={cn("text-xs text-slate-400 leading-relaxed", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({ className, children, ...props }) {
  return (
    <div className={cn("pt-0", className)} {...props}>
      {children}
    </div>
  );
}
