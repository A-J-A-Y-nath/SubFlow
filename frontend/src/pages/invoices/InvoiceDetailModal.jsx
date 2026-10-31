import React, { useState } from "react";
import { CheckCircle, XCircle, Calendar, User, Hash, CreditCard, Printer } from "lucide-react";
import Modal from "../../components/ui/Modal";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Alert from "../../components/common/Alert";
import { formatCurrency, formatDate } from "../../lib/utils";
import subflowService from "../../services/subflowService";

export function InvoiceDetailModal({ isOpen, onClose, invoice, isAdminOrStaff, onRefresh }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  if (!invoice) return null;

  const canConfirm = invoice.status === "draft";
  const canCancel  = ["draft", "posted", "overdue", "partial"].includes(invoice.status);
  const isPaid     = invoice.status === "paid";
  const isOverdue  = invoice.status === "overdue";

  const handleAction = async (action) => {
    setError(null); setSuccess(null); setIsLoading(true);
    try {
      if (action === "confirm") {
        await subflowService.confirmInvoice(invoice.id);
        setSuccess("Invoice confirmed and posted.");
      } else if (action === "cancel") {
        await subflowService.cancelInvoice(invoice.id);
        setSuccess("Invoice cancelled.");
      }
      onRefresh?.();
    } catch (err) {
      setError(err.message || "Action failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const handlePrint = () => window.print();

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Invoice — ${invoice.invoice_number}`}
      description="Full invoice detail, line items, payments, and actions."
      maxWidth="max-w-2xl"
    >
      <div className="space-y-5">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
        {success && <Alert type="success" message={success} />}

        {/* Status banner */}
        <div className={`flex flex-wrap items-center gap-3 p-4 rounded-xl border ${
          isOverdue
            ? "bg-rose-500/10 border-rose-500/30"
            : isPaid
            ? "bg-emerald-500/10 border-emerald-500/30"
            : "bg-slate-950/60 border-slate-800"
        }`}>
          <Badge status={invoice.status}>{invoice.status}</Badge>
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            {[
              [User,     "Customer",   invoice.customer_name],
              [Hash,     "Sub #",      invoice.subscription_number || "Manual"],
              [Calendar, "Issue Date", formatDate(invoice.invoice_date)],
              [Calendar, "Due Date",   formatDate(invoice.due_date)],
            ].map(([Icon, label, value]) => (
              <div key={label}>
                <p className="text-slate-500 mb-0.5 flex items-center gap-1"><Icon className="w-3 h-3" /> {label}</p>
                <p className={`font-medium truncate ${isOverdue && label === "Due Date" ? "text-rose-300" : "text-slate-200"}`}>{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Billing period */}
        {invoice.billing_period_start && (
          <div className="text-xs p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-400">
            Billing period: <span className="text-slate-200 font-medium">
              {formatDate(invoice.billing_period_start)} — {formatDate(invoice.billing_period_end)}
            </span>
          </div>
        )}

        {/* Financials */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          {[
            ["Subtotal",     formatCurrency(invoice.subtotal, invoice.currency)],
            ["Discount",     `−${formatCurrency(invoice.discount_amount, invoice.currency)}`],
            ["Tax (GST)",    formatCurrency(invoice.tax_amount, invoice.currency)],
            ["Total",        formatCurrency(invoice.total_amount, invoice.currency)],
            ["Paid",         formatCurrency(invoice.amount_paid, invoice.currency)],
            ["Balance Due",  formatCurrency(invoice.balance_due, invoice.currency)],
          ].map(([label, value]) => (
            <div key={label} className={`p-3 rounded-lg border ${
              label === "Balance Due" && parseFloat(invoice.balance_due) > 0
                ? "bg-rose-500/10 border-rose-500/20"
                : label === "Paid" && parseFloat(invoice.amount_paid) > 0
                ? "bg-emerald-500/10 border-emerald-500/20"
                : "bg-slate-900 border-slate-800"
            }`}>
              <p className="text-slate-500 mb-0.5">{label}</p>
              <p className={`font-bold ${
                label === "Total" || label === "Balance Due" ? "text-white text-sm" :
                label === "Paid" ? "text-emerald-300" : "text-slate-200"
              }`}>{value}</p>
            </div>
          ))}
        </div>

        {/* Line Items */}
        {invoice.lines?.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Line Items</p>
            <div className="rounded-xl border border-slate-800 overflow-hidden">
              <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-slate-800/60 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <div className="col-span-4">Description</div>
                <div className="col-span-2">Product</div>
                <div className="col-span-1 text-right">Qty</div>
                <div className="col-span-2 text-right">Unit Price</div>
                <div className="col-span-1 text-right">Disc%</div>
                <div className="col-span-2 text-right">Line Total</div>
              </div>
              {invoice.lines.map((line) => (
                <div key={line.id} className="grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-slate-800 text-xs">
                  <div className="col-span-4 text-slate-300">{line.description}</div>
                  <div className="col-span-2 text-slate-400">{line.product_name || "—"}</div>
                  <div className="col-span-1 text-right text-slate-300">{line.quantity}</div>
                  <div className="col-span-2 text-right text-slate-300">{formatCurrency(line.unit_price, invoice.currency)}</div>
                  <div className="col-span-1 text-right text-slate-400">{line.discount_percent}%</div>
                  <div className="col-span-2 text-right text-white font-semibold">{formatCurrency(line.line_total, invoice.currency)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Payment Allocations */}
        {invoice.payment_allocations?.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1">
              <CreditCard className="w-3 h-3" /> Payment Allocations
            </p>
            <div className="space-y-1.5">
              {invoice.payment_allocations.map((pa, i) => (
                <div key={pa.id || i} className="flex justify-between items-center text-xs p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <span className="text-slate-400">Payment #{pa.payment_id}</span>
                  <span className="text-emerald-300 font-semibold">{formatCurrency(pa.allocated_amount, invoice.currency)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {invoice.notes && (
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
            <strong className="text-slate-400">Notes: </strong>{invoice.notes}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800">
          <div className="flex flex-wrap items-center gap-2">
            {isAdminOrStaff && (
              <>
                <span className="text-xs text-slate-500 mr-1">Staff Actions:</span>
                {canConfirm && (
                  <Button variant="primary" size="sm" onClick={() => handleAction("confirm")} isLoading={isLoading}>
                    <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Confirm & Post
                  </Button>
                )}
                {canCancel && (
                  <Button variant="danger" size="sm" onClick={() => handleAction("cancel")} isLoading={isLoading}>
                    <XCircle className="w-3.5 h-3.5 mr-1.5" /> Cancel Invoice
                  </Button>
                )}
              </>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={handlePrint}>
            <Printer className="w-3.5 h-3.5 mr-1.5" /> Print Invoice
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default InvoiceDetailModal;
