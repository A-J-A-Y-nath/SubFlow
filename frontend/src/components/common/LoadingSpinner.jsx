import React from "react";
import { Loader2 } from "lucide-react";

export function LoadingSpinner({ message = "Loading data...", size = "md", fullPage = false }) {
  const sizes = {
    sm: "w-4 h-4",
    md: "w-8 h-8",
    lg: "w-12 h-12",
  };

  const content = (
    <div className="flex flex-col items-center justify-center gap-3 p-6">
      <Loader2 className={`${sizes[size]} animate-spin text-brand-500`} />
      {message && <p className="text-xs font-medium text-slate-400 animate-pulse">{message}</p>}
    </div>
  );

  if (fullPage) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
        {content}
      </div>
    );
  }

  return content;
}

export default LoadingSpinner;
