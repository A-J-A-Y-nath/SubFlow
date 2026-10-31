import React, { useEffect } from "react";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

export function Modal({ isOpen, onClose, title, description, children, footer, maxWidth = "max-w-lg" }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && isOpen) onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Dialog box */}
      <div
        className={cn(
          "relative w-full rounded-2xl border border-slate-700/80 bg-slate-900 p-6 shadow-2xl transition-all z-10",
          maxWidth
        )}
      >
        <div className="flex items-start justify-between pb-4 border-b border-slate-800">
          <div>
            {title && <h3 className="text-lg font-bold text-white">{title}</h3>}
            {description && <p className="text-xs text-slate-400 mt-1">{description}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="py-4 text-sm text-slate-200">{children}</div>

        {footer && (
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
