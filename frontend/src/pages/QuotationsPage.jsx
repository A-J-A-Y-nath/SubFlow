import React, { useState, useEffect, useCallback } from "react";
import { FileText, Plus, RefreshCw } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";
import CreateQuotationModal from "./quotations/CreateQuotationModal";
import QuotationDetailModal from "./quotations/QuotationDetailModal";

const STATUS_FILTERS = ["all", "draft", "sent", "approved", "expired"];

export function QuotationsPage() {
  const { isAdmin, isStaff } = useAuth();
  const isAdminOrStaff = isAdmin || isStaff;

  const [quotations, setQuotations] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedQuo, setSelectedQuo] = useState(null);

  const fetchQuotations = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { page, per_page: 15 };
      if (statusFilter !== "all") params.status = statusFilter;
      const res = await subflowService.getQuotations(params);
      if (res.success) {
        setQuotations(res.data?.items || []);
        setPagination(res.data?.pagination || null);
      }
    } catch (err) {
      setError(err.message || "Failed to load quotations.");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => { fetchQuotations(); }, [fetchQuotations]);
  useEffect(() => { setPage(1); }, [statusFilter]);

  // When detail modal refreshes, re-fetch so status updates appear
  const handleRefresh = useCallback(() => {
    fetchQuotations();
    // Re-fetch selected quotation detail
    if (selectedQuo) {
      subflowService.getQuotationById(selectedQuo.id)
        .then((res) => { if (res.success) setSelectedQuo(res.data); })
        .catch(() => setSelectedQuo(null));
    }
  }, [fetchQuotations, selectedQuo]);

  const handleRowClick = async (quo) => {
    try {
      const res = await subflowService.getQuotationById(quo.id);
      setSelectedQuo(res.data || quo);
    } catch {
      setSelectedQuo(quo);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Quotations & Proposals</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Prepare, send, and convert pricing estimates into active subscriptions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchQuotations}
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition"
            title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
          {isAdminOrStaff && (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1.5" /> New Quotation
            </Button>
          )}
        </div>
      </div>

      {/* Status Filters */}
      <div className="flex flex-wrap items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 w-fit">
        {STATUS_FILTERS.map((st) => (
          <button key={st} onClick={() => setStatusFilter(st)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
              statusFilter === st ? "bg-brand-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
            }`}>
            {st}
          </button>
        ))}
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {isLoading ? (
        <LoadingSpinner message="Loading quotations…" />
      ) : quotations.length === 0 ? (
        <EmptyState
          title="No Quotations Found"
          description={statusFilter !== "all"
            ? `No "${statusFilter}" quotations found.`
            : "Create a quotation to send a pricing proposal to a customer."}
          icon={FileText}
          actionText={isAdminOrStaff ? "Draft Quotation" : undefined}
          onAction={isAdminOrStaff ? () => setShowCreate(true) : undefined}
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quotation #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Issue Date</TableHead>
                <TableHead>Valid Until</TableHead>
                <TableHead>Total</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {quotations.map((q) => {
                const isExpiring = q.status === "sent" &&
                  new Date(q.valid_until) <= new Date(Date.now() + 3 * 24 * 60 * 60 * 1000);
                return (
                  <TableRow key={q.id} onClick={() => handleRowClick(q)}
                    className="cursor-pointer hover:bg-slate-800/40 transition">
                    <TableCell className="font-mono text-xs font-semibold text-brand-400">
                      {q.quotation_number}
                    </TableCell>
                    <TableCell className="font-medium text-white">{q.customer_name || "—"}</TableCell>
                    <TableCell className="text-xs text-slate-300">{q.plan_name || "Custom"}</TableCell>
                    <TableCell className="text-xs text-slate-400">{formatDate(q.issue_date)}</TableCell>
                    <TableCell className={`text-xs font-medium ${isExpiring ? "text-amber-400" : "text-slate-300"}`}>
                      {formatDate(q.valid_until)}
                      {isExpiring && <span className="ml-1 text-[10px] text-amber-500">(expiring soon)</span>}
                    </TableCell>
                    <TableCell className="font-semibold text-slate-200">
                      {formatCurrency(q.total_amount, q.currency)}
                    </TableCell>
                    <TableCell><Badge status={q.status}>{q.status}</Badge></TableCell>
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

      <CreateQuotationModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onSuccess={() => { setShowCreate(false); fetchQuotations(); }}
      />
      <QuotationDetailModal
        isOpen={!!selectedQuo}
        onClose={() => setSelectedQuo(null)}
        quotation={selectedQuo}
        onRefresh={handleRefresh}
      />
    </div>
  );
}

export default QuotationsPage;
