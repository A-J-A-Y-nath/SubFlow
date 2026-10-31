import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = "USD") {
  const num = typeof amount === "number" ? amount : parseFloat(amount || 0);
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `$${num.toFixed(2)}`;
  }
}

export function formatDate(dateString) {
  if (!dateString) return "—";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(date);
  } catch {
    return dateString;
  }
}

export function getStatusColor(status) {
  const s = String(status || "").toLowerCase();
  switch (s) {
    case "paid":
    case "active":
    case "completed":
    case "approved":
    case "valid":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "partial":
    case "partially paid":
    case "pending":
    case "paused":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "overdue":
    case "failed":
    case "cancelled":
    case "rejected":
    case "expired":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "posted":
    case "sent":
    case "issued":
      return "bg-blue-500/15 text-blue-300 border-blue-500/30";
    case "draft":
    default:
      return "bg-slate-500/15 text-slate-300 border-slate-500/30";
  }
}
