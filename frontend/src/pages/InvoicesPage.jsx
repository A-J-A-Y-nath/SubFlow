import React, { useState, useEffect, useMemo } from "react";
import {
  Receipt,
  Plus,
  Search,
  RefreshCw,
  Printer,
  Calendar,
  AlertCircle,
  Clock,
  ArrowRight,
  Trash2,
  PlayCircle,
  FileText,
  DollarSign,
  CheckCircle2,
  XCircle,
  ExternalLink
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

export function InvoicesPage() {
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "admin" || user?.role === "staff";

  // Data state
  const [invoices, setInvoices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Summary state
  const [receivablesSummary, setReceivablesSummary] = useState(null);

  // Detail Modal
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);

  // Create Invoice Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [activeSubscriptions, setActiveSubscriptions] = useState([]);
  const [createForm, setCreateForm] = useState({
    customer_id: "",
    subscription_id: "",
    invoice_date: new Date().toISOString().split("T")[0],
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
    payment_terms: "Net 30",
    currency: "USD",
    notes: "",
    status: "draft",
    coupon_code: "",
    tax_amount: 0,
    lines: [
      { product_id: "", description: "Subscription Service", quantity: 1, unit_price: 29.0, discount_percent: 0 }
    ]
  });
  const [couponFeedback, setCouponFeedback] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Recurring Billing Modal
  const [isRecurringOpen, setIsRecurringOpen] = useState(false);
  const [billingDate, setBillingDate] = useState(new Date().toISOString().split("T")[0]);
  const [previewResult, setPreviewResult] = useState(null);
  const [isProcessingRecurring, setIsProcessingRecurring] = useState(false);

  // Load Invoices & Summary
  const fetchInvoices = async () => {
    try {
      setError(null);
      const params = {};
      if (statusFilter !== "all") params.status = statusFilter;
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const [invRes, sumRes] = await Promise.all([
        subflowService.getInvoices(params),
        subflowService.getReceivablesSummary().catch(() => null)
      ]);

      if (invRes.success) {
        setInvoices(invRes.data?.items || []);
      }
      if (sumRes?.success) {
        setReceivablesSummary(sumRes.data?.summary || null);
      }
    } catch (err) {
      setError(err.message || "Failed to load invoices.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, [statusFilter]);

  // Load dropdown data when create modal opens
  const openCreateModal = async () => {
    setIsCreateOpen(true);
    setCouponFeedback(null);
    try {
      const [custRes, prodRes, subRes] = await Promise.all([
        subflowService.getInvoicingCustomers().catch(() => ({ data: [] })),
        subflowService.getProducts().catch(() => ({ data: { items: [] } })),
        subflowService.getInvoicingSubscriptions().catch(() => ({ data: [] }))
      ]);

      setCustomers(custRes.data || []);
      setProducts(prodRes.data?.items || []);
      setActiveSubscriptions(subRes.data || []);

      if (custRes.data?.length > 0 && !createForm.customer_id) {
        setCreateForm((prev) => ({ ...prev, customer_id: custRes.data[0].id }));
      }
    } catch (e) {
      console.error(e);
    }
  };

  // View invoice detail
  const handleViewInvoice = async (invoiceId) => {
    setIsLoadingDetail(true);
    try {
      const res = await subflowService.getInvoice(invoiceId);
      if (res.success) {
        setSelectedInvoice(res.data);
      }
    } catch (err) {
      setError(err.message || "Failed to load invoice details.");
    } finally {
      setIsLoadingDetail(false);
    }
  };

  // Issue Draft Invoice
  const handleIssueInvoice = async (invoiceId) => {
    try {
      const res = await subflowService.issueInvoice(invoiceId);
      if (res.success) {
        setSuccessMsg(`Invoice ${res.data?.invoice_number} successfully posted!`);
        setSelectedInvoice(null);
        fetchInvoices();
      }
    } catch (err) {
      setError(err.message || "Failed to issue invoice.");
    }
  };

  // Cancel Invoice
  const handleCancelInvoice = async (invoiceId) => {
    if (!window.confirm("Are you sure you want to cancel this invoice? This action cannot be reversed.")) return;
    try {
      const res = await subflowService.cancelInvoice(invoiceId);
      if (res.success) {
        setSuccessMsg(`Invoice ${res.data?.invoice_number} cancelled.`);
        setSelectedInvoice(null);
        fetchInvoices();
      }
    } catch (err) {
      setError(err.message || "Failed to cancel invoice.");
    }
  };

  // Create line item management
  const handleAddLine = () => {
    setCreateForm((prev) => ({
      ...prev,
      lines: [
        ...prev.lines,
        { product_id: "", description: "Additional Service", quantity: 1, unit_price: 10.0, discount_percent: 0 }
      ]
    }));
  };

  const handleRemoveLine = (idx) => {
    setCreateForm((prev) => ({
      ...prev,
      lines: prev.lines.filter((_, i) => i !== idx)
    }));
  };

  const handleLineChange = (idx, field, value) => {
    setCreateForm((prev) => {
      const newLines = [...prev.lines];
      newLines[idx] = { ...newLines[idx], [field]: value };

      // Auto-populate price when product selected
      if (field === "product_id" && value) {
        const prod = products.find((p) => p.id === parseInt(value));
        if (prod) {
          newLines[idx].description = prod.name;
          newLines[idx].unit_price = prod.default_price || 0;
        }
      }
      return { ...prev, lines: newLines };
    });
  };

  // Calculate live preview totals
  const formCalculations = useMemo(() => {
    let subtotal = 0;
    createForm.lines.forEach((line) => {
      const qty = parseFloat(line.quantity || 0);
      const price = parseFloat(line.unit_price || 0);
      const disc = parseFloat(line.discount_percent || 0);
      const gross = qty * price;
      const lineTotal = gross * (1 - disc / 100);
      subtotal += Math.max(0, lineTotal);
    });

    const tax = parseFloat(createForm.tax_amount || 0);
    const discount = couponFeedback?.calculated_discount || 0;
    const total = Math.max(0, subtotal - discount + tax);

    return { subtotal, discount, tax, total };
  }, [createForm.lines, createForm.tax_amount, couponFeedback]);

  // Live validate coupon in form
  const handleValidateCoupon = async () => {
    if (!createForm.coupon_code.trim()) return;
    try {
      const res = await subflowService.validateCoupon(createForm.coupon_code.trim(), {
        amount: formCalculations.subtotal
      });
      if (res.success) {
        setCouponFeedback({
          code: res.data.code,
          calculated_discount: res.data.calculated_discount,
          message: `Coupon '${res.data.code}' applied! -$${res.data.calculated_discount.toFixed(2)}`
        });
      }
    } catch (err) {
      setCouponFeedback({
        error: err.message || "Invalid coupon code"
      });
    }
  };

  // Submit invoice creation
  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (createForm.lines.length === 0) {
      setError("Please add at least one line item.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        customer_id: parseInt(createForm.customer_id),
        subscription_id: createForm.subscription_id ? parseInt(createForm.subscription_id) : null,
        invoice_date: createForm.invoice_date,
        due_date: createForm.due_date,
        payment_terms: createForm.payment_terms,
        currency: createForm.currency,
        notes: createForm.notes,
        status: createForm.status,
        coupon_code: createForm.coupon_code.trim() || null,
        tax_amount: parseFloat(createForm.tax_amount || 0),
        lines: createForm.lines.map((l) => ({
          product_id: l.product_id ? parseInt(l.product_id) : null,
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          discount_percent: parseFloat(l.discount_percent || 0)
        }))
      };

      const res = await subflowService.createInvoice(payload);
      if (res.success) {
        setSuccessMsg(`Invoice ${res.data?.invoice_number} created successfully!`);
        setIsCreateOpen(false);
        fetchInvoices();
      }
    } catch (err) {
      setError(err.message || "Failed to create invoice.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Recurring billing preview & run
  const handlePreviewRecurring = async () => {
    setIsProcessingRecurring(true);
    try {
      const res = await subflowService.previewRecurringBilling({ target_date: billingDate });
      if (res.success) {
        setPreviewResult(res.data);
      }
    } catch (err) {
      setError(err.message || "Failed to preview recurring billing.");
    } finally {
      setIsProcessingRecurring(false);
    }
  };

  const handleExecuteRecurring = async () => {
    setIsProcessingRecurring(true);
    try {
      const res = await subflowService.runRecurringBilling({ target_date: billingDate, dry_run: false });
      if (res.success) {
        setSuccessMsg(`Recurring billing complete: ${res.data?.generated_invoices?.length || 0} invoices generated.`);
        setIsRecurringOpen(false);
        setPreviewResult(null);
        fetchInvoices();
      }
    } catch (err) {
      setError(err.message || "Recurring billing run failed.");
    } finally {
      setIsProcessingRecurring(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Receivables KPI Strip */}
      {receivablesSummary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Recorded Revenue</span>
            <p className="text-xl font-bold text-emerald-400 mt-1">
              {formatCurrency(receivablesSummary.total_revenue)}
            </p>
            <span className="text-[10px] text-slate-500">Collected settled payments</span>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Outstanding Receivables</span>
            <p className="text-xl font-bold text-amber-400 mt-1">
              {formatCurrency(receivablesSummary.outstanding_amount)}
            </p>
            <span className="text-[10px] text-slate-500">{receivablesSummary.outstanding_count} unpaid invoices</span>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Overdue Balance</span>
            <p className="text-xl font-bold text-rose-400 mt-1">
              {formatCurrency(receivablesSummary.overdue_amount)}
            </p>
            <span className="text-[10px] text-slate-500">{receivablesSummary.overdue_count} past due date</span>
          </div>
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Collection Rate</span>
            <p className="text-xl font-bold text-white mt-1">
              {receivablesSummary.collection_rate_percent}%
            </p>
            <span className="text-[10px] text-slate-500">Revenue / Total Billed</span>
          </div>
        </div>
      )}

      {/* Header & Action Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Invoices & Receivables</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Automated recurring statements, accounts receivable, and balance reconciliation
          </p>
        </div>

        <div className="flex items-center gap-2">
          {isStaffOrAdmin && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setIsRecurringOpen(true);
                  setPreviewResult(null);
                }}
                className="text-xs font-semibold"
              >
                <PlayCircle className="w-3.5 h-3.5 mr-1.5 text-brand-400" />
                Recurring Billing
              </Button>
              <Button variant="primary" size="sm" onClick={openCreateModal}>
                <Plus className="w-4 h-4 mr-1.5" />
                Create Invoice
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Notifications */}
      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
        {/* Search */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search invoice #, customer name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchInvoices()}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-1 overflow-x-auto pb-1 md:pb-0">
          {["all", "draft", "posted", "partial", "paid", "overdue", "cancelled"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition-all ${
                statusFilter === st
                  ? "bg-brand-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              {st === "posted" ? "Issued" : st === "partial" ? "Partially Paid" : st}
            </button>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setIsRefreshing(true);
              fetchInvoices();
            }}
            className="p-1.5 ml-1"
            title="Refresh List"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Main Invoices Table */}
      {isLoading ? (
        <LoadingSpinner message="Loading invoice statements..." />
      ) : invoices.length === 0 ? (
        <EmptyState
          title="No Invoices Found"
          description={
            statusFilter !== "all"
              ? `No invoices match the filter '${statusFilter}'.`
              : "Invoices will generate automatically on subscription billing cycles or when created manually."
          }
          icon={Receipt}
          actionText={isStaffOrAdmin ? "Create First Invoice" : undefined}
          onAction={isStaffOrAdmin ? openCreateModal : undefined}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Invoice #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Issue Date</TableHead>
              <TableHead>Due Date</TableHead>
              <TableHead>Total Amount</TableHead>
              <TableHead>Paid</TableHead>
              <TableHead>Balance Due</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((inv) => (
              <TableRow key={inv.id} className="hover:bg-slate-800/40 transition">
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {inv.invoice_number}
                </TableCell>
                <TableCell className="font-medium text-white">
                  {inv.customer_name || "Client"}
                </TableCell>
                <TableCell className="text-xs text-slate-400">
                  {formatDate(inv.invoice_date)}
                </TableCell>
                <TableCell className="text-xs text-slate-300 font-medium">
                  {formatDate(inv.due_date)}
                </TableCell>
                <TableCell className="font-semibold text-slate-200">
                  {formatCurrency(inv.total_amount, inv.currency)}
                </TableCell>
                <TableCell className="text-xs text-emerald-400 font-medium">
                  {formatCurrency(inv.amount_paid, inv.currency)}
                </TableCell>
                <TableCell className="font-bold text-slate-100">
                  {formatCurrency(inv.balance_due, inv.currency)}
                </TableCell>
                <TableCell>
                  <Badge status={inv.status}>
                    {inv.status === "posted" ? "Issued" : inv.status === "partial" ? "Partially Paid" : inv.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-right space-x-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleViewInvoice(inv.id)}
                    className="text-xs py-1 px-2.5 h-auto text-slate-300 hover:text-white"
                  >
                    View
                  </Button>
                  {isStaffOrAdmin && inv.status === "draft" && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleIssueInvoice(inv.id)}
                      className="text-xs py-1 px-2.5 h-auto"
                    >
                      Issue
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {/* Invoice Detail & Print Modal */}
      {selectedInvoice && (
        <Modal
          isOpen={Boolean(selectedInvoice)}
          onClose={() => setSelectedInvoice(null)}
          title={`Invoice ${selectedInvoice.invoice_number}`}
          size="lg"
        >
          <div className="space-y-6 print:p-0">
            {/* Printable Invoice Card */}
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-6">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-5">
                <div>
                  <h3 className="text-2xl font-black text-white tracking-tight">SUBFLOW</h3>
                  <p className="text-xs text-slate-400 mt-1">Enterprise Subscription & Billing Management</p>
                </div>
                <div className="text-right">
                  <span className="font-mono text-sm font-bold text-brand-400">{selectedInvoice.invoice_number}</span>
                  <div className="mt-1">
                    <Badge status={selectedInvoice.status}>{selectedInvoice.status}</Badge>
                  </div>
                </div>
              </div>

              {/* Meta Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-slate-500 uppercase font-medium">Billed To</span>
                  <p className="font-semibold text-white mt-0.5">{selectedInvoice.customer_name || "Client"}</p>
                  <p className="text-slate-400">Customer ID: #{selectedInvoice.customer_id}</p>
                </div>
                <div>
                  <span className="text-slate-500 uppercase font-medium">Issue Date</span>
                  <p className="font-semibold text-white mt-0.5">{formatDate(selectedInvoice.invoice_date)}</p>
                </div>
                <div>
                  <span className="text-slate-500 uppercase font-medium">Due Date</span>
                  <p className="font-semibold text-white mt-0.5">{formatDate(selectedInvoice.due_date)}</p>
                </div>
                <div>
                  <span className="text-slate-500 uppercase font-medium">Payment Terms</span>
                  <p className="font-semibold text-white mt-0.5">{selectedInvoice.payment_terms || "Net 30"}</p>
                </div>
              </div>

              {/* Lines Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left">
                  <thead className="border-b border-slate-800 text-slate-400 uppercase font-medium">
                    <tr>
                      <th className="py-2">Description</th>
                      <th className="py-2 text-center">Qty</th>
                      <th className="py-2 text-right">Unit Price</th>
                      <th className="py-2 text-right">Disc %</th>
                      <th className="py-2 text-right">Line Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {(selectedInvoice.lines || []).map((l, idx) => (
                      <tr key={idx}>
                        <td className="py-2.5 font-medium text-white">{l.description}</td>
                        <td className="py-2.5 text-center text-slate-300">{l.quantity}</td>
                        <td className="py-2.5 text-right text-slate-300">{formatCurrency(l.unit_price, selectedInvoice.currency)}</td>
                        <td className="py-2.5 text-right text-slate-400">{l.discount_percent > 0 ? `${l.discount_percent}%` : "—"}</td>
                        <td className="py-2.5 text-right font-semibold text-slate-100">{formatCurrency(l.line_total, selectedInvoice.currency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Financial Breakdown */}
              <div className="flex justify-end pt-3 border-t border-slate-800">
                <div className="w-64 space-y-2 text-xs">
                  <div className="flex justify-between text-slate-400">
                    <span>Subtotal:</span>
                    <span>{formatCurrency(selectedInvoice.subtotal, selectedInvoice.currency)}</span>
                  </div>
                  {selectedInvoice.discount_amount > 0 && (
                    <div className="flex justify-between text-emerald-400">
                      <span>Discount:</span>
                      <span>-{formatCurrency(selectedInvoice.discount_amount, selectedInvoice.currency)}</span>
                    </div>
                  )}
                  {selectedInvoice.tax_amount > 0 && (
                    <div className="flex justify-between text-slate-400">
                      <span>Tax:</span>
                      <span>+{formatCurrency(selectedInvoice.tax_amount, selectedInvoice.currency)}</span>
                    </div>
                  )}
                  <div className="flex justify-between text-sm font-bold text-white pt-2 border-t border-slate-800">
                    <span>Total:</span>
                    <span>{formatCurrency(selectedInvoice.total_amount, selectedInvoice.currency)}</span>
                  </div>
                  <div className="flex justify-between text-xs text-emerald-400">
                    <span>Amount Paid:</span>
                    <span>{formatCurrency(selectedInvoice.amount_paid, selectedInvoice.currency)}</span>
                  </div>
                  <div className="flex justify-between text-sm font-black text-brand-400 pt-1 border-t border-slate-800/60">
                    <span>Balance Due:</span>
                    <span>{formatCurrency(selectedInvoice.balance_due, selectedInvoice.currency)}</span>
                  </div>
                </div>
              </div>

              {/* Payment Allocations History */}
              {selectedInvoice.allocations && selectedInvoice.allocations.length > 0 && (
                <div className="pt-4 border-t border-slate-800/80">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                    Payment Receipts Applied ({selectedInvoice.allocations.length})
                  </h4>
                  <div className="divide-y divide-slate-800/60 text-xs">
                    {selectedInvoice.allocations.map((alloc) => (
                      <div key={alloc.id} className="py-1.5 flex items-center justify-between">
                        <span className="font-mono text-brand-400">{alloc.payment_number}</span>
                        <span className="text-slate-400 capitalize">{alloc.payment_method?.replace("_", " ")}</span>
                        <span className="text-slate-400">{formatDate(alloc.payment_date)}</span>
                        <span className="font-semibold text-emerald-400">+{formatCurrency(alloc.amount_allocated)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {selectedInvoice.notes && (
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 text-xs text-slate-400">
                  <strong className="text-slate-300">Notes:</strong> {selectedInvoice.notes}
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => window.print()}
                className="text-xs"
              >
                <Printer className="w-3.5 h-3.5 mr-1.5" />
                Print Invoice
              </Button>

              <div className="flex items-center gap-2">
                {isStaffOrAdmin && selectedInvoice.status === "draft" && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleIssueInvoice(selectedInvoice.id)}
                  >
                    Issue Statement
                  </Button>
                )}
                {isStaffOrAdmin && selectedInvoice.status !== "cancelled" && selectedInvoice.status !== "paid" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleCancelInvoice(selectedInvoice.id)}
                    className="text-rose-400 hover:text-rose-300"
                  >
                    Cancel Invoice
                  </Button>
                )}
                <Button variant="secondary" size="sm" onClick={() => setSelectedInvoice(null)}>
                  Close
                </Button>
              </div>
            </div>
          </div>
        </Modal>
      )}

      {/* Create Invoice Modal */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title="Create New Invoice"
          size="lg"
        >
          <form onSubmit={handleCreateSubmit} className="space-y-4">
            {/* Customer & Subscription */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Customer Client <span className="text-rose-400">*</span>
                </label>
                <select
                  value={createForm.customer_id}
                  onChange={(e) => setCreateForm({ ...createForm, customer_id: e.target.value })}
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

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Link to Subscription (Optional)
                </label>
                <select
                  value={createForm.subscription_id}
                  onChange={(e) => setCreateForm({ ...createForm, subscription_id: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="">None (One-off / Custom Invoice)</option>
                  {activeSubscriptions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.subscription_number} — {s.plan_name} (${s.recurring_amount})
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Dates & Terms */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Issue Date</label>
                <Input
                  type="date"
                  value={createForm.invoice_date}
                  onChange={(e) => setCreateForm({ ...createForm, invoice_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Due Date</label>
                <Input
                  type="date"
                  value={createForm.due_date}
                  onChange={(e) => setCreateForm({ ...createForm, due_date: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Payment Terms</label>
                <select
                  value={createForm.payment_terms}
                  onChange={(e) => setCreateForm({ ...createForm, payment_terms: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="Net 15">Net 15 Days</option>
                  <option value="Net 30">Net 30 Days</option>
                  <option value="Net 60">Net 60 Days</option>
                  <option value="Due on Receipt">Due on Receipt</option>
                </select>
              </div>
            </div>

            {/* Line Items Builder */}
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-white uppercase tracking-wider">
                  Line Items ({createForm.lines.length})
                </span>
                <Button type="button" variant="ghost" size="sm" onClick={handleAddLine} className="text-xs">
                  <Plus className="w-3.5 h-3.5 mr-1" /> Add Line Item
                </Button>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {createForm.lines.map((line, idx) => (
                  <div key={idx} className="flex items-center gap-2 p-2 rounded-lg bg-slate-950 border border-slate-800">
                    <div className="flex-1">
                      <Input
                        placeholder="Description..."
                        value={line.description}
                        onChange={(e) => handleLineChange(idx, "description", e.target.value)}
                        required
                      />
                    </div>
                    <div className="w-20">
                      <Input
                        type="number"
                        placeholder="Qty"
                        min="1"
                        step="1"
                        value={line.quantity}
                        onChange={(e) => handleLineChange(idx, "quantity", e.target.value)}
                        required
                      />
                    </div>
                    <div className="w-24">
                      <Input
                        type="number"
                        placeholder="Price"
                        min="0"
                        step="0.01"
                        value={line.unit_price}
                        onChange={(e) => handleLineChange(idx, "unit_price", e.target.value)}
                        required
                      />
                    </div>
                    <div className="w-20">
                      <Input
                        type="number"
                        placeholder="Disc %"
                        min="0"
                        max="100"
                        value={line.discount_percent}
                        onChange={(e) => handleLineChange(idx, "discount_percent", e.target.value)}
                      />
                    </div>
                    {createForm.lines.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveLine(idx)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Coupon & Live Validation */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Promotional Coupon</label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter coupon code (e.g. SAVE20)..."
                    value={createForm.coupon_code}
                    onChange={(e) => {
                      setCreateForm({ ...createForm, coupon_code: e.target.value.toUpperCase() });
                      setCouponFeedback(null);
                    }}
                  />
                  <Button type="button" variant="secondary" size="sm" onClick={handleValidateCoupon}>
                    Apply
                  </Button>
                </div>
                {couponFeedback?.message && (
                  <p className="text-[11px] text-emerald-400 mt-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> {couponFeedback.message}
                  </p>
                )}
                {couponFeedback?.error && (
                  <p className="text-[11px] text-rose-400 mt-1 flex items-center gap-1">
                    <XCircle className="w-3 h-3" /> {couponFeedback.error}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Estimated Tax ($)</label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={createForm.tax_amount}
                  onChange={(e) => setCreateForm({ ...createForm, tax_amount: e.target.value })}
                />
              </div>
            </div>

            {/* Calculations Summary Box */}
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between text-xs">
              <span className="text-slate-400">
                Subtotal: <strong className="text-white">${formCalculations.subtotal.toFixed(2)}</strong> |
                Discount: <strong className="text-emerald-400">-${formCalculations.discount.toFixed(2)}</strong> |
                Tax: <strong className="text-slate-300">+${formCalculations.tax.toFixed(2)}</strong>
              </span>
              <span className="text-sm font-bold text-brand-400">
                Total: ${formCalculations.total.toFixed(2)}
              </span>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Internal Notes</label>
              <textarea
                rows={2}
                value={createForm.notes}
                onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
                placeholder="Optional customer notes or instructions..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            {/* Submit buttons */}
            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="secondary"
                disabled={isSubmitting}
                onClick={() => setCreateForm((prev) => ({ ...prev, status: "draft" }))}
              >
                Save as Draft
              </Button>
              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting}
                onClick={() => setCreateForm((prev) => ({ ...prev, status: "posted" }))}
              >
                {isSubmitting ? "Creating..." : "Create & Issue"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Recurring Billing Runner Modal */}
      {isRecurringOpen && (
        <Modal
          isOpen={isRecurringOpen}
          onClose={() => setIsRecurringOpen(false)}
          title="Automated Recurring Billing Engine"
          size="md"
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-400">
              The billing engine processes active subscriptions whose scheduled billing dates have arrived.
              Duplicate invoices for the same period are automatically skipped.
            </p>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Execution Target Date</label>
              <Input
                type="date"
                value={billingDate}
                onChange={(e) => setBillingDate(e.target.value)}
              />
            </div>

            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handlePreviewRecurring}
                disabled={isProcessingRecurring}
                className="flex-1"
              >
                {isProcessingRecurring ? "Checking..." : "Preview Due Subscriptions"}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleExecuteRecurring}
                disabled={isProcessingRecurring}
                className="flex-1"
              >
                {isProcessingRecurring ? "Processing..." : "Run Billing Cycle Now"}
              </Button>
            </div>

            {previewResult && (
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-2">
                <div className="flex justify-between font-semibold text-white">
                  <span>Eligible Subscriptions:</span>
                  <span className="text-brand-400">{previewResult.total_due_subscriptions}</span>
                </div>
                {previewResult.generated_invoices?.length > 0 ? (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {previewResult.generated_invoices.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-slate-400">
                        <span>{item.subscription_number} ({item.customer_name})</span>
                        <span className="font-semibold text-emerald-400">${item.estimated_total || item.total_amount}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 italic">No subscriptions currently due on this date.</p>
                )}
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
}

export default InvoicesPage;
