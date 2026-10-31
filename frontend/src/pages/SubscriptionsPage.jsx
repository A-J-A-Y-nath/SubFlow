import React, { useState, useEffect, useCallback } from "react";
import { Repeat, Plus, RefreshCw } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";
import CreateSubscriptionModal from "./subscriptions/CreateSubscriptionModal";
import SubscriptionDetailModal from "./subscriptions/SubscriptionDetailModal";

const STATUS_FILTERS = ["all", "draft", "active", "paused", "cancelled", "expired"];

export function SubscriptionsPage() {
  const { isAdmin, isStaff } = useAuth();
  const isAdminOrStaff = isAdmin || isStaff;

  const [subscriptions, setSubscriptions] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);

  const [showCreate, setShowCreate] = useState(false);
  const [selectedSub, setSelectedSub] = useState(null);

  const fetchSubscriptions = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = { page, per_page: 15 };
      if (statusFilter !== "all") params.status = statusFilter;
      const res = await subflowService.getSubscriptions(params);
      if (res.success) {
        setSubscriptions(res.data?.items || []);
        setPagination(res.data?.pagination || null);
      }
    } catch (err) {
      setError(err.message || "Failed to load subscriptions.");
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    fetchSubscriptions();
  }, [fetchSubscriptions]);

  // Reset page on filter change
  useEffect(() => { setPage(1); }, [statusFilter]);

  const handleRowClick = (sub) => setSelectedSub(sub);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Subscriptions</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Monitor recurring contracts, renewals, and billing schedules
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchSubscriptions}
            className="p-2 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          {isAdminOrStaff && (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              <Plus className="w-4 h-4 mr-1.5" /> New Subscription
            </Button>
          )}
        </div>
      </div>

      {/* Status Filter Pills */}
      <div className="flex flex-wrap items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 w-fit">
        {STATUS_FILTERS.map((st) => (
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

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading subscriptions…" />
      ) : subscriptions.length === 0 ? (
        <EmptyState
          title="No Subscriptions Found"
          description={
            statusFilter !== "all"
              ? `No subscriptions with status "${statusFilter}".`
              : "Subscriptions created from quotations or manually will appear here."
          }
          icon={Repeat}
          actionText={isAdminOrStaff ? "Create Subscription" : undefined}
          onAction={isAdminOrStaff ? () => setShowCreate(true) : undefined}
        />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Subscription #</TableHead>
                <TableHead>Customer</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Start Date</TableHead>
                <TableHead>Next Billing</TableHead>
                <TableHead>Recurring</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {subscriptions.map((sub) => (
                <TableRow
                  key={sub.id}
                  onClick={() => handleRowClick(sub)}
                  className="cursor-pointer hover:bg-slate-800/40 transition"
                >
                  <TableCell className="font-mono text-xs font-semibold text-brand-400">
                    {sub.subscription_number}
                  </TableCell>
                  <TableCell className="font-medium text-white">{sub.customer_name || "—"}</TableCell>
                  <TableCell className="text-xs text-slate-300">{sub.plan_name || "Custom"}</TableCell>
                  <TableCell className="text-xs text-slate-400">{formatDate(sub.start_date)}</TableCell>
                  <TableCell className="text-xs text-slate-300 font-medium">
                    {formatDate(sub.next_billing_date)}
                  </TableCell>
                  <TableCell className="font-semibold text-slate-200">
                    {formatCurrency(sub.recurring_amount, sub.currency)}
                  </TableCell>
                  <TableCell>
                    <Badge status={sub.status}>{sub.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* Pagination */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
              <span>
                Page {pagination.page} of {pagination.total_pages} — {pagination.total_items} total
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => p - 1)}
                  disabled={!pagination.has_prev}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!pagination.has_next}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 disabled:opacity-40 hover:border-slate-500 transition"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      <CreateSubscriptionModal
        isOpen={showCreate}
        onClose={() => setShowCreate(false)}
        onSuccess={() => { setShowCreate(false); fetchSubscriptions(); }}
      />
      <SubscriptionDetailModal
        isOpen={!!selectedSub}
        onClose={() => setSelectedSub(null)}
        subscription={selectedSub}
        isAdminOrStaff={isAdminOrStaff}
        onRefresh={() => { fetchSubscriptions(); setSelectedSub(null); }}
      />
    </div>
  );
}

export default SubscriptionsPage;
