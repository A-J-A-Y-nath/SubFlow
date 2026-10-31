import React, { useState } from "react";
import {
  RefreshCw, PauseCircle, XCircle, PlayCircle,
  Calendar, Hash, CreditCard, User, Layers
} from "lucide-react";
import Modal from "../../components/ui/Modal";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Alert from "../../components/common/Alert";
import { formatCurrency, formatDate } from "../../lib/utils";
import subflowService from "../../services/subflowService";

const STATUS_ACTIONS = {
  draft:     [{ label: "Activate",  next: "active",    icon: PlayCircle,   variant: "primary"  },
              { label: "Cancel",    next: "cancelled",  icon: XCircle,      variant: "danger"   }],
  active:    [{ label: "Pause",     next: "paused",     icon: PauseCircle,  variant: "warning"  },
              { label: "Cancel",    next: "cancelled",  icon: XCircle,      variant: "danger"   }],
  paused:    [{ label: "Resume",    next: "active",     icon: PlayCircle,   variant: "primary"  },
              { label: "Cancel",    next: "cancelled",  icon: XCircle,      variant: "danger"   }],
  expired:   [{ label: "Renew",     next: null,         icon: RefreshCw,    variant: "primary", isRenew: true }],
  cancelled: [],
};

export function SubscriptionDetailModal({ isOpen, onClose, subscription, isAdminOrStaff, onRefresh }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!subscription) return null;
  const actions = STATUS_ACTIONS[subscription.status] || [];

  const handleAction = async (action) => {
    setError(null);
    setSuccess(null);
    setIsLoading(true);
    try {
      if (action.isRenew) {
        await subflowService.renewSubscription(subscription.id);
        setSuccess("Subscription renewed successfully.");
      } else {
        await subflowService.updateSubscriptionStatus(subscription.id, action.next);
        setSuccess(`Status updated to "${action.next}".`);
      }
      onRefresh?.();
    } catch (err) {
      setError(err.message || "Action failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Subscription — ${subscription.subscription_number}`}
      description="Full subscription detail, line items, and lifecycle actions."
      maxWidth="max-w-2xl"
    >
      <div className="space-y-5">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
        {success && <Alert type="success" message={success} />}

        {/* Status + Key Info */}
        <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <Badge status={subscription.status}>{subscription.status}</Badge>
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <p className="text-slate-500 mb-0.5 flex items-center gap-1"><User className="w-3 h-3" /> Customer</p>
              <p className="text-slate-200 font-medium truncate">{subscription.customer_name || "—"}</p>
            </div>
            <div>
              <p className="text-slate-500 mb-0.5 flex items-center gap-1"><Layers className="w-3 h-3" /> Plan</p>
              <p className="text-slate-200 font-medium truncate">{subscription.plan_name || "—"}</p>
            </div>
            <div>
              <p className="text-slate-500 mb-0.5 flex items-center gap-1"><Calendar className="w-3 h-3" /> Start</p>
              <p className="text-slate-200 font-medium">{formatDate(subscription.start_date)}</p>
            </div>
            <div>
              <p className="text-slate-500 mb-0.5 flex items-center gap-1"><Calendar className="w-3 h-3" /> Next Billing</p>
              <p className="text-slate-200 font-medium">{formatDate(subscription.next_billing_date)}</p>
            </div>
          </div>
        </div>

        {/* Billing Period */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          {[
            ["Period Start", formatDate(subscription.current_period_start)],
            ["Period End",   formatDate(subscription.current_period_end)],
            ["Recurring",    formatCurrency(subscription.recurring_amount, subscription.currency)],
            ["Auto-Renew",   subscription.auto_renew ? "Yes" : "No"],
            ["Currency",     subscription.currency],
          ].map(([label, value]) => (
            <div key={label} className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <p className="text-slate-500 mb-0.5">{label}</p>
              <p className="text-slate-100 font-semibold">{value}</p>
            </div>
          ))}
        </div>

        {/* Line Items */}
        {subscription.lines?.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Line Items</p>
            <div className="rounded-xl border border-slate-800 overflow-hidden">
              <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-slate-800/60 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <div className="col-span-4">Product</div>
                <div className="col-span-3">Description</div>
                <div className="col-span-1 text-right">Qty</div>
                <div className="col-span-2 text-right">Unit Price</div>
                <div className="col-span-2 text-right">Line Total</div>
              </div>
              {subscription.lines.map((line) => {
                const lineTotal = line.quantity * line.unit_price * (1 - line.discount_percent / 100);
                return (
                  <div key={line.id} className="grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-slate-800 text-xs">
                    <div className="col-span-4 text-slate-300 font-medium">{line.product_name || `#${line.product_id}`}</div>
                    <div className="col-span-3 text-slate-400 truncate">{line.description}</div>
                    <div className="col-span-1 text-right text-slate-300">{line.quantity}</div>
                    <div className="col-span-2 text-right text-slate-300">{formatCurrency(line.unit_price, subscription.currency)}</div>
                    <div className="col-span-2 text-right text-white font-semibold">{formatCurrency(lineTotal, subscription.currency)}</div>
                  </div>
                );
              })}
              <div className="flex justify-end gap-2 px-3 py-2.5 border-t border-slate-700 bg-slate-800/40">
                <span className="text-xs text-slate-400">Recurring Total:</span>
                <span className="text-sm font-bold text-white">{formatCurrency(subscription.recurring_amount, subscription.currency)}</span>
              </div>
            </div>
          </div>
        )}

        {/* Cancel Reason */}
        {subscription.cancel_reason && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300">
            <strong>Cancellation reason:</strong> {subscription.cancel_reason}
          </div>
        )}

        {/* Lifecycle Actions — admin/staff only */}
        {isAdminOrStaff && actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800">
            <span className="text-xs text-slate-500 mr-1">Actions:</span>
            {actions.map((action) => (
              <Button
                key={action.label}
                variant={action.variant}
                size="sm"
                onClick={() => handleAction(action)}
                isLoading={isLoading}
                disabled={isLoading}
              >
                <action.icon className="w-3.5 h-3.5 mr-1.5" />
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

export default SubscriptionDetailModal;
