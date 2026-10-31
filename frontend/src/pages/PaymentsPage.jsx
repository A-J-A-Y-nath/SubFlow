import React, { useState, useEffect } from "react";
import { CreditCard, Plus, ArrowUpRight } from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

export function PaymentsPage() {
  const [payments, setPayments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchPayments() {
      try {
        const res = await subflowService.getPayments();
        if (isMounted && res.success) {
          setPayments(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load payments.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchPayments();
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Payment Transactions</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Gateway transaction logs, reconciliation records, and balance allocations
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => alert("Payments Developer will connect payment record dialog here!")}>
          <Plus className="w-4 h-4 mr-1.5" />
          Record Payment
        </Button>
      </div>

      {/* Developer note */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Payments API endpoint: <code className="text-slate-200">GET /api/v1/payments</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading payments transactions..." />
      ) : payments.length === 0 ? (
        <EmptyState
          title="No Payment Transactions Logged"
          description="Customer payment transactions processed via credit card, bank transfer, or cash will be recorded here."
          developerNote="Model: backend/models/payment.py | Controller: backend/routes/payments.py"
          icon={CreditCard}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Payment #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Invoice #</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Transaction Ref</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {payments.map((pay) => (
              <TableRow key={pay.id}>
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {pay.payment_number}
                </TableCell>
                <TableCell className="font-medium text-white">{pay.customer_name || "Client"}</TableCell>
                <TableCell className="font-mono text-xs text-slate-400">
                  {pay.invoice_number || "—"}
                </TableCell>
                <TableCell className="text-xs capitalize text-slate-300">
                  {pay.payment_method?.replace("_", " ") || "Card"}
                </TableCell>
                <TableCell className="font-mono text-xs text-slate-500">
                  {pay.transaction_reference || "—"}
                </TableCell>
                <TableCell className="font-semibold text-emerald-400">
                  {formatCurrency(pay.amount, pay.currency)}
                </TableCell>
                <TableCell>
                  <Badge status={pay.status}>{pay.status}</Badge>
                </TableCell>
                <TableCell className="text-xs text-slate-400">{formatDate(pay.payment_date)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

export default PaymentsPage;
