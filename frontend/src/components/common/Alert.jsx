import React from "react";
import { AlertCircle, CheckCircle2, Info, AlertTriangle, X } from "lucide-react";
import { cn } from "../../lib/utils";

export function Alert({ type = "error", title, message, details, onClose, className }) {
  const styles = {
    error: {
      container: "bg-rose-500/10 border-rose-500/30 text-rose-300",
      icon: AlertCircle,
      iconColor: "text-rose-400",
    },
    success: {
      container: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
      icon: CheckCircle2,
      iconColor: "text-emerald-400",
    },
    info: {
      container: "bg-sky-500/10 border-sky-500/30 text-sky-300",
      icon: Info,
      iconColor: "text-sky-400",
    },
    warning: {
      container: "bg-amber-500/10 border-amber-500/30 text-amber-300",
      icon: AlertTriangle,
      iconColor: "text-amber-400",
    },
  };

  const current = styles[type] || styles.error;
  const IconComponent = current.icon;

  return (
    <div
      className={cn(
        "flex items-start gap-3 p-4 rounded-xl border text-sm backdrop-blur-sm transition-all",
        current.container,
        className
      )}
    >
      <IconComponent className={cn("w-5 h-5 shrink-0 mt-0.5", current.iconColor)} />
      <div className="flex-1 space-y-1">
        {title && <h5 className="font-semibold text-white text-sm">{title}</h5>}
        {message && <div className="text-xs leading-relaxed opacity-90">{message}</div>}
        {Array.isArray(details) && details.length > 0 && (
          <ul className="list-disc list-inside text-xs mt-1.5 space-y-0.5 opacity-90">
            {details.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        )}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-white/10 transition text-inherit opacity-70 hover:opacity-100"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default Alert;
