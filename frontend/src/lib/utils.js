import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount, currency = "USD") {
  const numericAmount = typeof amount === "number" ? amount : parseFloat(amount) || 0;
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(numericAmount);
  } catch (e) {
    return `${currency || "USD"} ${numericAmount.toFixed(2)}`;
  }
}

export function formatDate(dateString) {
  if (!dateString) return "N/A";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "N/A";
    return new Intl.DateTimeFormat("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    }).format(date);
  } catch (e) {
    return dateString;
  }
}

export function getStatusColor(status) {
  const s = (status || "").toLowerCase();
  switch (s) {
    case "active":
    case "paid":
    case "approved":
    case "posted":
    case "completed":
      return "bg-emerald-500/15 text-emerald-300 border-emerald-500/30";
    case "draft":
    case "pending":
    case "sent":
    case "partial":
    case "trial":
      return "bg-amber-500/15 text-amber-300 border-amber-500/30";
    case "cancelled":
    case "rejected":
    case "overdue":
    case "expired":
    case "inactive":
    case "failed":
      return "bg-rose-500/15 text-rose-300 border-rose-500/30";
    case "paused":
      return "bg-purple-500/15 text-purple-300 border-purple-500/30";
    default:
      return "bg-slate-800 text-slate-300 border-slate-700";
  }
}
