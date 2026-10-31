import React, { useState, useEffect, useCallback } from "react";
import { Receipt, Plus, RefreshCw, Zap } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";
import CreateInvoiceModal from "./invoices/CreateInvoiceModal";
import InvoiceDetailModal from "./invoices/InvoiceDetailModal";

const STATUS_FILTERS = ["all", "draft", "posted", "partial", "paid", "overdue", "cancelled"];

export function InvoicesPage() {
  const { isAdmin, isStaff } = useAuth();
  const isAdminOrStaff = isAdmin || isStaff;

  const [invoices, setInvoices] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);
  const [billingMsg, setBillingMsg] = useState(null);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedInv, setSelectedInv] = useState(null);
  const [isBillingRunning, setIsBillingRunning] = useState(false);

  const fetchInvoices = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { page, per_page: 15 };
      if (statusFilter !== "all") params.status = statusFilter;
      const res = await subflowService.getInvoices(params);
      if (res.success) {
        setInvoices(res.data?.items || []);
        setPagination(res.data?.pagination || null);
      }
    } catch (err) {
      setError(err.message || "Failed to load invoices.");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);
  useEffect(() => { setPage(1); }, [statusFilter]);

  const handleRowClick = async (inv) => {
    try {
      const res = await subflowService.getInvoiceById(inv.id);
      setSelectedInv(res.data || inv);
    } catch {
      setSelectedInv(inv);
    }
  };

  const handleRunBilling = async () => {
    setIsBillingRunning(true);
    setBillingMsg(null);
    try {
      const res = await subflowService.runBillingCycle();
      const { processed, invoices_created, already_billed, errors } = res.data;
      setBillingMsg(
        `Billing cycle complete: ${processed} subscriptions processed, ` +
        `${invoices_created} new invoice(s) created, ` +
        `${already_billed} already billed, ` +
        `${errors.length} error(s).`
      );
      fetchInvoices();
    } catch (err) {
      setBillingMsg(`Billing failed: ${err.message}`);
    } finally {
      setIsBillingRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Invoices & Receivables</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Recurring billing statements, payment tracking, and outstanding balances
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={fetchInvoices}
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition"
            title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
          {isAdmin && (
            <Button variant="outline" size="sm" onClick={handleRunBilling} isLoading={isBillingRunning}>
              <Zap className="w-4 h-4 mr-1.5" />
              {isBillingRunning ? "Running…" : "Run Billing Cycle"}
            </Button>
          )}
          {isAdminOrStaff && (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1.5" /> New Invoice
            </Button>
          )}
        </div>
      </div>

      {/* Billing cycle result */}
      {billingMsg && (
        <Alert
          type={billingMsg.startsWith("Billing failed") ? "error" : "success"}
          message={billingMsg}
          onClose={() => setBillingMsg(null)}
        />
      )}

      {/* Status Filter Pills */}
      <div className="flex flex-wrap items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 w-fit">
        {STATUS_FILTERS.map((st) => (
          <button key={st} onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              statusFilter === st
                ? st === "overdue"
                  ? "bg-rose-600 text-white shadow"
                  : "bg-brand-600 text-white shadow"
                : "text-slate-400 hover:text-slate-200"
            }`}>
            {st}
          </button>
        ))}
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {isLoading ? (
        <LoadingSpinner message="Loading invoices…" />
      ) : invoices.length === 0 ? (
        <EmptyState
          title="No Invoices Found"
          description={statusFilter !== "all"
            ? `No "${statusFilter}" invoices found.`
            : "Invoices are generated from subscription billing cycles or manually created."}
          icon={Receipt}
          actionText={isAdminOrStaff ? "Issue Invoice" : undefined}
          onAction={isAdminOrStaff ? () => setShowCreate(true) : undefined}
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Invoice #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Issue Date</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Paid</TableHead>
                <TableHead>Balance</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoices.map((inv) => {
                const isOverdue = inv.status === "overdue";
                const balanceDue = parseFloat(inv.balance_due) || 0;
                return (
                  <TableRow key={inv.id} onClick={() => handleRowClick(inv)}
                    className={`cursor-pointer transition ${isOverdue ? "bg-rose-500/5 hover:bg-rose-500/10" : "hover:bg-slate-800/40"}`}>
                    <TableCell className="font-mono text-xs font-semibold text-brand-400">
                      {inv.invoice_number}
                    </TableCell>
                    <TableCell className="font-medium text-white">{inv.customer_name || "—"}</TableCell>
                    <TableCell className="text-xs text-slate-400">{formatDate(inv.invoice_date)}</TableCell>
                    <TableCell className={`text-xs font-medium ${isOverdue ? "text-rose-400" : "text-slate-300"}`}>
                      {formatDate(inv.due_date)}
                    </TableCell>
                    <TableCell className="font-semibold text-slate-200">
                      {formatCurrency(inv.total_amount, inv.currency)}
                    </TableCell>
                    <TableCell className="text-xs text-emerald-400 font-medium">
                      {formatCurrency(inv.amount_paid, inv.currency)}
                    </TableCell>
                    <TableCell className={`font-bold ${balanceDue > 0 ? (isOverdue ? "text-rose-300" : "text-amber-300") : "text-emerald-300"}`}>
                      {formatCurrency(inv.balance_due, inv.currency)}
                    </TableCell>
                    <TableCell><Badge status={inv.status}>{inv.status}</Badge></TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
              <span>Page {pagination.page} of {pagination.total_pages} — {pagination.total_items} total</span>
              <div className="flex gap-2">
                <button onClick={() => setPage((p) => p - 1)} disabled={!pagination.has_prev}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition">
                  Previous
                </button>
                <button onClick={() => setPage((p) => p + 1)} disabled={!pagination.has_next}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition">
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      <CreateInvoiceModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onSuccess={() => { setShowCreate(false); fetchInvoices(); }}
      />
      <InvoiceDetailModal
        isOpen={!!selectedInv}
        onClose={() => setSelectedInv(null)}
        invoice={selectedInv}
        isAdminOrStaff={isAdminOrStaff}
        onRefresh={() => { fetchInvoices(); setSelectedInv(null); }}
      />
    </div>
  );
}

export default InvoicesPage;
