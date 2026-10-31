import React from "react";
import { FolderPlus, Layers } from "lucide-react";
import { Button } from "../ui/Button";

export function EmptyState({
  title = "No records found",
  description = "No data has been created for this module yet. As records are processed, they will appear here.",
  icon: Icon = Layers,
  actionText,
  onAction,
  developerNote,
  className = "",
}) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 sm:p-12 text-center rounded-2xl border border-dashed border-slate-800 bg-slate-900/30 backdrop-blur-sm ${className}`}>
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 mb-4 shadow-lg shadow-brand-500/5">
        <Icon className="h-8 w-8" />
      </div>

      <h3 className="text-base font-semibold text-slate-100">{title}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm leading-relaxed">
        {description}
      </p>

      {developerNote && (
        <div className="mt-3 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-[11px] text-slate-400 font-mono">
          <span className="text-brand-400 font-semibold">Dev Module Interface:</span> {developerNote}
        </div>
      )}

      {actionText && onAction && (
        <div className="mt-5">
          <Button variant="primary" size="sm" onClick={onAction}>
            <FolderPlus className="w-4 h-4 mr-1.5" />
            {actionText}
          </Button>
        </div>
      )}
    </div>
  );
}

export default EmptyState;
