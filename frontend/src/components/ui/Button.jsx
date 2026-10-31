import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

export const Button = React.forwardRef(
  ({ className, variant = "primary", size = "md", isLoading = false, disabled, children, ...props }, ref) => {
    const baseStyles = "inline-flex items-center justify-center font-medium rounded-lg transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-900 disabled:opacity-50 disabled:cursor-not-allowed select-none";

    const variants = {
      primary: "bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-500/20 focus:ring-brand-500 active:scale-[0.98]",
      secondary: "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700 focus:ring-slate-500",
      outline: "border border-slate-700 hover:border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800/50 focus:ring-slate-500",
      ghost: "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 focus:ring-slate-500",
      danger: "bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-500/20 focus:ring-rose-500",
      success: "bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-500/20 focus:ring-emerald-500",
    };

    const sizes = {
      sm: "text-xs px-2.5 py-1.5 gap-1.5",
      md: "text-sm px-4 py-2 gap-2",
      lg: "text-base px-5 py-2.5 gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading && <Loader2 className="w-4 h-4 animate-spin shrink-0" />}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
export default Button;
