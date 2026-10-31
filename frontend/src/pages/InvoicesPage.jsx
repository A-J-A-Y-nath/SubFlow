import React, { useState, useEffect } from "react";
import { Receipt, Plus, DollarSign } from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

export function InvoicesPage() {
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchInvoices() {
      try {
        const params = statusFilter !== "all" ? { status: statusFilter } : {};
        const res = await subflowService.getInvoices(params);
        if (isMounted && res.success) {
          setInvoices(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load invoices.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchInvoices();
    return () => {
      isMounted = false;
    };
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Invoices & Receivables</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated recurring statements, payment collection tracking, and balances
          </p>
        </div>

        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {["all", "draft", "posted", "paid", "overdue"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                statusFilter === st
                  ? "bg-brand-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Developer note */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Invoicing & Ledger API endpoint: <code className="text-slate-200">GET /api/v1/invoices</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading invoice statements..." />
      ) : invoices.length === 0 ? (
        <EmptyState
          title="No Invoices Recorded"
          description="Invoices automatically generate on subscription billing dates or when quotations are approved."
          developerNote="Model: backend/models/invoice.py | Controller: backend/routes/invoices.py"
          icon={Receipt}
          actionText="Issue New Invoice"
          onAction={() => alert("Billing Developer will connect invoice generation dialog here!")}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Issue Date</TableHead>
              <TableHead>Due Date</TableHead>
              <TableHead>Total</TableHead>
              <TableHead>Amount Paid</TableHead>
              <TableHead>Balance Due</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((inv) => (
              <TableRow key={inv.id}>
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {inv.invoice_number}
                </TableCell>
                <TableCell className="font-medium text-white">{inv.customer_name || "Client"}</TableCell>
                <TableCell className="text-xs text-slate-400">{formatDate(inv.invoice_date)}</TableCell>
                <TableCell className="text-xs text-slate-300 font-medium">{formatDate(inv.due_date)}</TableCell>
                <TableCell className="font-semibold text-slate-200">
                  {formatCurrency(inv.total_amount, inv.currency)}
                </TableCell>
                <TableCell className="text-xs text-emerald-400">
                  {formatCurrency(inv.amount_paid, inv.currency)}
                </TableCell>
                <TableCell className="font-bold text-slate-100">
                  {formatCurrency(inv.balance_due, inv.currency)}
                </TableCell>
                <TableCell>
                  <Badge status={inv.status}>{inv.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

export default InvoicesPage;
