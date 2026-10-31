import React, { useState, useEffect } from "react";
import {
  CreditCard,
  Plus,
  Search,
  RefreshCw,
  DollarSign,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  Layers,
  AlertCircle
} from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Modal from "../components/ui/Modal";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";
import { useAuth } from "../hooks/useAuth";

export function PaymentsPage() {
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "admin" || user?.role === "staff";

  // Data state
  const [payments, setPayments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("all");
  const [methodFilter, setMethodFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Record Payment Modal
  const [isRecordOpen, setIsRecordOpen] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [customerInvoices, setCustomerInvoices] = useState([]);
  const [recordForm, setRecordForm] = useState({
    customer_id: "",
    amount: "",
    currency: "USD",
    payment_method: "credit_card",
    status: "completed",
    transaction_reference: "",
    invoice_id: "",
    notes: "",
    payment_date: new Date().toISOString().split("T")[0]
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Detail & Allocation Modal
  const [selectedPayment, setSelectedPayment] = useState(null);
  const [unpaidInvoices, setUnpaidInvoices] = useState([]);
  const [allocationInputs, setAllocationInputs] = useState({});
  const [isAllocating, setIsAllocating] = useState(false);

  // Fetch payments
  const fetchPayments = async () => {
    try {
      setError(null);
      const params = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (methodFilter !== "all") params.payment_method = methodFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const res = await subflowService.getPayments(params);
      if (res.success) {
        setPayments(res.data?.items || []);
      }
    } catch (err) {
      setError(err.message || "Failed to load payment transactions.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchPayments();
  }, [statusFilter, methodFilter]);

  // Open record modal
  const openRecordModal = async () => {
    setIsRecordOpen(true);
    try {
      const custRes = await subflowService.getInvoicingCustomers();
      if (custRes.success) {
        setCustomers(custRes.data || []);
        if (custRes.data?.length > 0 && !recordForm.customer_id) {
          handleCustomerChange(custRes.data[0].id);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Load invoices for customer when selected in form
  const handleCustomerChange = async (customerId) => {
    setRecordForm((prev) => ({ ...prev, customer_id: customerId, invoice_id: "" }));
    if (!customerId) {
      setCustomerInvoices([]);
      return;
    }
    try {
      const res = await subflowService.getInvoices({ customer_id: customerId, status: "posted" });
      if (res.success) {
        setCustomerInvoices(res.data?.items || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  // Submit payment record
  const handleRecordSubmit = async (e) => {
    e.preventDefault();
    if (!recordForm.customer_id || !recordForm.amount) {
      setError("Customer and Amount are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        customer_id: parseInt(recordForm.customer_id),
        amount: parseFloat(recordForm.amount),
        currency: recordForm.currency,
        payment_method: recordForm.payment_method,
        status: recordForm.status,
        transaction_reference: recordForm.transaction_reference.trim() || null,
        invoice_id: recordForm.invoice_id ? parseInt(recordForm.invoice_id) : null,
        notes: recordForm.notes,
        payment_date: recordForm.payment_date
      };

      const res = await subflowService.recordPayment(payload);
      if (res.success) {
        setSuccessMsg(`Payment ${res.data?.payment_number} recorded successfully!`);
        setIsRecordOpen(false);
        setRecordForm({
          customer_id: "",
          amount: "",
          currency: "USD",
          payment_method: "credit_card",
          status: "completed",
          transaction_reference: "",
          invoice_id: "",
          notes: "",
          payment_date: new Date().toISOString().split("T")[0]
        });
        fetchPayments();
      }
    } catch (err) {
      setError(err.message || "Failed to record payment transaction.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // View payment & load allocation data
  const handleViewPayment = async (paymentId) => {
    try {
      const res = await subflowService.getPayment(paymentId);
      if (res.success) {
        setSelectedPayment(res.data);
        setAllocationInputs({});

        // If payment is completed and has unallocated amount, fetch unpaid invoices for customer
        if (res.data.status === "completed" && res.data.unallocated_amount > 0) {
          const invRes = await subflowService.getInvoices({
            customer_id: res.data.customer_id,
            status: "posted"
          });
          if (invRes.success) {
            setUnpaidInvoices(invRes.data?.items?.filter((i) => i.balance_due > 0) || []);
          }
        } else {
          setUnpaidInvoices([]);
        }
      }
    } catch (err) {
      setError(err.message || "Failed to load payment transaction details.");
    }
  };

  // Submit allocations
  const handleAllocateSubmit = async () => {
    const allocationsToSubmit = Object.entries(allocationInputs)
      .map(([invId, amt]) => ({ invoice_id: parseInt(invId), amount: parseFloat(amt) }))
      .filter((a) => a.amount > 0);

    if (allocationsToSubmit.length === 0) {
      setError("Please specify an amount to allocate to at least one invoice.");
      return;
    }

    setIsAllocating(true);
    try {
      const res = await subflowService.allocatePayment(selectedPayment.id, allocationsToSubmit);
      if (res.success) {
        setSuccessMsg("Payment successfully allocated across invoices!");
        handleViewPayment(selectedPayment.id);
        fetchPayments();
      }
    } catch (err) {
      setError(err.message || "Allocation failed.");
    } finally {
      setIsAllocating(false);
    }
  };

  // Calculated KPI counters
  const paymentStats = React.useMemo(() => {
    let totalRevenue = 0;
    let completedCount = 0;
    let pendingCount = 0;
    payments.forEach((p) => {
      if (p.status === "completed") {
        totalRevenue += parseFloat(p.amount || 0);
        completedCount++;
      } else if (p.status === "pending") {
        pendingCount++;
      }
    });
    return { totalRevenue, completedCount, pendingCount };
  }, [payments]);

  return (
    <div className="space-y-6">
      {/* Top Summary KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Recorded Receipts</span>
          <p className="text-xl font-bold text-emerald-400 mt-1">{formatCurrency(paymentStats.totalRevenue)}</p>
          <span className="text-[10px] text-slate-500">From {paymentStats.completedCount} completed receipts</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Completed Transactions</span>
          <p className="text-xl font-bold text-white mt-1">{paymentStats.completedCount}</p>
          <span className="text-[10px] text-slate-500">Fully settled payments</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Pending Processing</span>
          <p className="text-xl font-bold text-amber-400 mt-1">{paymentStats.pendingCount}</p>
          <span className="text-[10px] text-slate-500">Awaiting gateway settlement</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Avg Receipt Size</span>
          <p className="text-xl font-bold text-brand-400 mt-1">
            {formatCurrency(paymentStats.completedCount > 0 ? paymentStats.totalRevenue / paymentStats.completedCount : 0)}
          </p>
          <span className="text-[10px] text-slate-500">Average transaction volume</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Payment Transactions</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Gateway transaction logs, reconciliation records, and balance allocations
          </p>
        </div>

        {isStaffOrAdmin && (
          <Button variant="primary" size="sm" onClick={openRecordModal}>
            <Plus className="w-4 h-4 mr-1.5" />
            Record Payment
          </Button>
        )}
      </div>

      {/* Notifications */}
      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Filters and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search payment #, transaction ref, customer..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchPayments()}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          {/* Method Filter */}
          <select
            value={methodFilter}
            onChange={(e) => setMethodFilter(e.target.value)}
            className="px-2.5 py-1 rounded-lg text-xs bg-slate-950 border border-slate-800 text-slate-300 focus:outline-none focus:border-brand-500"
          >
            <option value="all">All Methods</option>
            <option value="credit_card">Credit Card</option>
            <option value="bank_transfer">Bank Transfer</option>
            <option value="stripe">Stripe Gateway</option>
            <option value="cash">Cash / Cheque</option>
          </select>

          {/* Status Pills */}
          <div className="flex items-center gap-1">
            {["all", "completed", "pending", "failed"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition-all ${
                  statusFilter === st
                    ? "bg-brand-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setIsRefreshing(true);
              fetchPayments();
            }}
            className="p-1.5"
            title="Refresh List"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Main Table */}
      {isLoading ? (
        <LoadingSpinner message="Loading payments transactions..." />
      ) : payments.length === 0 ? (
        <EmptyState
          title="No Payment Transactions Logged"
          description="Customer payment transactions processed via credit card, bank transfer, or cash will be recorded here."
          icon={CreditCard}
          actionText={isStaffOrAdmin ? "Record New Payment" : undefined}
          onAction={isStaffOrAdmin ? openRecordModal : undefined}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Payment #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Target Invoice</TableHead>
              <TableHead>Method</TableHead>
              <TableHead>Transaction Ref</TableHead>
              <TableHead>Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Date</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {payments.map((pay) => (
              <TableRow key={pay.id} className="hover:bg-slate-800/40 transition">
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {pay.payment_number}
                </TableCell>
                <TableCell className="font-medium text-white">{pay.customer_name || "Client"}</TableCell>
                <TableCell className="font-mono text-xs text-slate-400">
                  {pay.invoice_number || "Unlinked / Direct"}
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
                <TableCell className="text-right">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewPayment(pay.id)}
                    className="text-xs py-1 px-2.5 h-auto text-slate-300 hover:text-white"
                  >
                    View & Reconcile
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Record Payment Modal */}
      {isRecordOpen && (
        <Modal
          isOpen={isRecordOpen}
          onClose={() => setIsRecordOpen(false)}
          title="Record Payment Receipt"
          size="md"
        >
          <form onSubmit={handleRecordSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Paying Customer <span className="text-rose-400">*</span>
              </label>
              <select
                value={recordForm.customer_id}
                onChange={(e) => handleCustomerChange(e.target.value)}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                required
              >
                <option value="">Select customer...</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.company_name} ({c.contact_name})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Payment Amount ($) <span className="text-rose-400">*</span>
                </label>
                <Input
                  type="number"
                  placeholder="0.00"
                  step="0.01"
                  min="0.01"
                  value={recordForm.amount}
                  onChange={(e) => setRecordForm({ ...recordForm, amount: e.target.value })}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Payment Method</label>
                <select
                  value={recordForm.payment_method}
                  onChange={(e) => setRecordForm({ ...recordForm, payment_method: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="credit_card">Credit Card</option>
                  <option value="bank_transfer">Bank Transfer / ACH</option>
                  <option value="stripe">Stripe Online</option>
                  <option value="cash">Cash / Cheque</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Payment Date</label>
                <Input
                  type="date"
                  value={recordForm.payment_date}
                  onChange={(e) => setRecordForm({ ...recordForm, payment_date: e.target.value })}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Transaction Ref / Cheque #</label>
                <Input
                  placeholder="e.g. ch_3M5qJ..."
                  value={recordForm.transaction_reference}
                  onChange={(e) => setRecordForm({ ...recordForm, transaction_reference: e.target.value })}
                />
              </div>
            </div>

            {/* Target Invoice */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Allocate to Outstanding Invoice (Optional)
              </label>
              <select
                value={recordForm.invoice_id}
                onChange={(e) => setRecordForm({ ...recordForm, invoice_id: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="">Leave Unallocated (Distribute Later)</option>
                {customerInvoices.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number} — Due: ${inv.balance_due} (Total: ${inv.total_amount})
                  </option>
                ))}
              </select>
              <span className="text-[10px] text-slate-500 mt-1 block">
                If selected, the payment will automatically settle the chosen invoice balance.
              </span>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Notes</label>
              <textarea
                rows={2}
                value={recordForm.notes}
                onChange={(e) => setRecordForm({ ...recordForm, notes: e.target.value })}
                placeholder="Optional payment or reconciliation memo..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <Button type="button" variant="ghost" onClick={() => setIsRecordOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? "Recording..." : "Record Payment"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Payment Detail & Reconciliation Modal */}
      {selectedPayment && (
        <Modal
          isOpen={Boolean(selectedPayment)}
          onClose={() => setSelectedPayment(null)}
          title={`Payment Receipt: ${selectedPayment.payment_number}`}
          size="lg"
        >
          <div className="space-y-6">
            {/* Payment Summary Header */}
            <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-slate-500 uppercase font-medium">Customer</span>
                <p className="font-semibold text-white mt-0.5">{selectedPayment.customer_name || "Client"}</p>
              </div>
              <div>
                <span className="text-slate-500 uppercase font-medium">Collected Amount</span>
                <p className="text-base font-bold text-emerald-400 mt-0.5">
                  {formatCurrency(selectedPayment.amount, selectedPayment.currency)}
                </p>
              </div>
              <div>
                <span className="text-slate-500 uppercase font-medium">Allocated Funds</span>
                <p className="font-semibold text-white mt-0.5">
                  {formatCurrency(selectedPayment.allocated_amount || 0, selectedPayment.currency)}
                </p>
              </div>
              <div>
                <span className="text-slate-500 uppercase font-medium">Unallocated Balance</span>
                <p className="text-base font-bold text-amber-400 mt-0.5">
                  {formatCurrency(selectedPayment.unallocated_amount || 0, selectedPayment.currency)}
                </p>
              </div>
            </div>

            {/* Existing Allocations List */}
            <div>
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Settled Invoices ({selectedPayment.allocations?.length || 0})
              </h4>
              {selectedPayment.allocations && selectedPayment.allocations.length > 0 ? (
                <div className="rounded-xl border border-slate-800 overflow-hidden">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-900 border-b border-slate-800 text-slate-400 uppercase font-medium">
                      <tr>
                        <th className="py-2.5 px-3">Invoice #</th>
                        <th className="py-2.5 px-3">Invoice Total</th>
                        <th className="py-2.5 px-3 text-right">Amount Allocated</th>
                        <th className="py-2.5 px-3">Allocation Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-950">
                      {selectedPayment.allocations.map((alloc) => (
                        <tr key={alloc.id}>
                          <td className="py-2.5 px-3 font-mono font-semibold text-brand-400">
                            {alloc.invoice_number || `Invoice #${alloc.invoice_id}`}
                          </td>
                          <td className="py-2.5 px-3 text-slate-300">{formatCurrency(alloc.invoice_total)}</td>
                          <td className="py-2.5 px-3 text-right font-bold text-emerald-400">
                            +{formatCurrency(alloc.amount_allocated)}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400">{formatDate(alloc.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-slate-500 italic p-3 rounded-lg bg-slate-900/50 border border-slate-800">
                  This payment has not yet been allocated to any invoice.
                </p>
              )}
            </div>

            {/* Allocate Unallocated Balance Section (Staff/Admin) */}
            {isStaffOrAdmin && selectedPayment.unallocated_amount > 0 && (
              <div className="p-4 rounded-xl bg-slate-900/80 border border-brand-500/30 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-brand-400" />
                      Allocate Remaining Balance ({formatCurrency(selectedPayment.unallocated_amount)})
                    </h5>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Distribute available funds against this customer's open invoices.
                    </p>
                  </div>
                </div>

                {unpaidInvoices.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {unpaidInvoices.map((inv) => (
                      <div
                        key={inv.id}
                        className="flex items-center justify-between gap-3 p-2.5 rounded-lg bg-slate-950 border border-slate-800"
                      >
                        <div className="text-xs">
                          <span className="font-mono font-semibold text-brand-400">{inv.invoice_number}</span>
                          <span className="text-slate-400 ml-2">Due Date: {formatDate(inv.due_date)}</span>
                          <span className="text-amber-400 font-semibold ml-2">Balance Due: ${inv.balance_due}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Input
                            type="number"
                            placeholder="Amount..."
                            min="0.01"
                            max={inv.balance_due}
                            step="0.01"
                            value={allocationInputs[inv.id] || ""}
                            onChange={(e) =>
                              setAllocationInputs({ ...allocationInputs, [inv.id]: e.target.value })
                            }
                            className="w-28 text-right text-xs"
                          />
                          <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            onClick={() => {
                              const canAlloc = Math.min(inv.balance_due, selectedPayment.unallocated_amount);
                              setAllocationInputs({ ...allocationInputs, [inv.id]: canAlloc });
                            }}
                            className="text-[10px] py-1 px-2 h-auto"
                          >
                            Max
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No open unpaid invoices found for this customer.</p>
                )}

                {unpaidInvoices.length > 0 && (
                  <div className="flex justify-end pt-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleAllocateSubmit}
                      disabled={isAllocating}
                    >
                      {isAllocating ? "Allocating..." : "Apply Allocation"}
                    </Button>
                  </div>
                )}
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setSelectedPayment(null)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

export default PaymentsPage;
