import React, { useState } from "react";
import { Send, CheckCircle, XCircle, Calendar, User, Layers, FileText } from "lucide-react";
import Modal from "../../components/ui/Modal";
import Badge from "../../components/ui/Badge";
import Button from "../../components/ui/Button";
import Input from "../../components/ui/Input";
import Alert from "../../components/common/Alert";
import { formatCurrency, formatDate } from "../../lib/utils";
import subflowService from "../../services/subflowService";

export function QuotationDetailModal({ isOpen, onClose, quotation, onRefresh }) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [showConfirmForm, setShowConfirmForm] = useState(false);
  const [startDate, setStartDate] = useState(new Date().toISOString().slice(0, 10));

  if (!quotation) return null;

  const canSend    = quotation.status === "draft";
  const canConfirm = quotation.status === "draft" || quotation.status === "sent";

  const handleSend = async () => {
    setError(null); setSuccess(null); setIsLoading(true);
    try {
      await subflowService.sendQuotation(quotation.id);
      setSuccess("Quotation sent to customer.");
      onRefresh?.();
    } catch (err) { setError(err.message || "Failed to send quotation."); }
    finally { setIsLoading(false); }
  };

  const handleConfirm = async (e) => {
    e.preventDefault();
    setError(null); setSuccess(null); setIsLoading(true);
    try {
      const res = await subflowService.confirmQuotation(quotation.id, { start_date: startDate });
      setSuccess(`Quotation approved! Subscription ${res.data?.subscription?.subscription_number} created.`);
      setShowConfirmForm(false);
      onRefresh?.();
    } catch (err) { setError(err.message || "Failed to confirm quotation."); }
    finally { setIsLoading(false); }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Quotation — ${quotation.quotation_number}`}
      description="Review quotation details and manage workflow actions."
      maxWidth="max-w-2xl"
    >
      <div className="space-y-5">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
        {success && <Alert type="success" message={success} />}

        {/* Status + Meta */}
        <div className="flex flex-wrap items-center gap-3 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
          <Badge status={quotation.status}>{quotation.status}</Badge>
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            {[
              [User,     "Customer",    quotation.customer_name],
              [Layers,   "Plan",        quotation.plan_name || "—"],
              [Calendar, "Issue Date",  formatDate(quotation.issue_date)],
              [Calendar, "Valid Until", formatDate(quotation.valid_until)],
            ].map(([Icon, label, value]) => (
              <div key={label}>
                <p className="text-slate-500 mb-0.5 flex items-center gap-1"><Icon className="w-3 h-3" /> {label}</p>
                <p className="text-slate-200 font-medium truncate">{value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Financials */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          {[
            ["Subtotal",  formatCurrency(quotation.subtotal, quotation.currency)],
            ["Discount",  `−${formatCurrency(quotation.discount_amount, quotation.currency)}`],
            ["Tax (GST)", formatCurrency(quotation.tax_amount, quotation.currency)],
            ["Total",     formatCurrency(quotation.total_amount, quotation.currency)],
          ].map(([label, value]) => (
            <div key={label} className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              <p className="text-slate-500 mb-0.5">{label}</p>
              <p className={`font-bold ${label === "Total" ? "text-white text-sm" : "text-slate-200"}`}>{value}</p>
            </div>
          ))}
        </div>

        {/* Line Items */}
        {quotation.lines?.length > 0 && (
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
              {quotation.lines.map((line) => (
                <div key={line.id} className="grid grid-cols-12 gap-2 px-3 py-2.5 border-t border-slate-800 text-xs">
                  <div className="col-span-4 text-slate-300 font-medium">{line.product_name || `#${line.product_id}`}</div>
                  <div className="col-span-3 text-slate-400 truncate">{line.description}</div>
                  <div className="col-span-1 text-right text-slate-300">{line.quantity}</div>
                  <div className="col-span-2 text-right text-slate-300">{formatCurrency(line.unit_price, quotation.currency)}</div>
                  <div className="col-span-2 text-right text-white font-semibold">{formatCurrency(line.total_amount, quotation.currency)}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Notes */}
        {quotation.notes && (
          <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
            <p className="text-xs font-semibold text-slate-400 mb-1 flex items-center gap-1">
              <FileText className="w-3 h-3" /> Notes
            </p>
            <p className="text-xs text-slate-300">{quotation.notes}</p>
          </div>
        )}

        {/* Confirm form */}
        {showConfirmForm && (
          <form onSubmit={handleConfirm} className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 space-y-3">
            <p className="text-sm font-semibold text-emerald-300">Confirm Quotation → Create Subscription</p>
            <Input label="Subscription Start Date" type="date" icon={Calendar}
              value={startDate} onChange={(e) => setStartDate(e.target.value)} required />
            <div className="flex gap-2">
              <Button type="submit" variant="primary" size="sm" isLoading={isLoading}>
                <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Confirm & Create
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => setShowConfirmForm(false)}>
                Back
              </Button>
            </div>
          </form>
        )}

        {/* Actions */}
        {!showConfirmForm && (canSend || canConfirm) && (
          <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800">
            <span className="text-xs text-slate-500 mr-1">Actions:</span>
            {canSend && (
              <Button variant="warning" size="sm" onClick={handleSend} isLoading={isLoading}>
                <Send className="w-3.5 h-3.5 mr-1.5" /> Send to Customer
              </Button>
            )}
            {canConfirm && (
              <Button variant="primary" size="sm" onClick={() => setShowConfirmForm(true)} disabled={isLoading}>
                <CheckCircle className="w-3.5 h-3.5 mr-1.5" /> Confirm & Subscribe
              </Button>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}

export default QuotationDetailModal;
