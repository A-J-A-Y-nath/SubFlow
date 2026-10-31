import React, { useState, useEffect } from "react";
import { Repeat, Plus, Filter, Calendar, RefreshCw } from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

export function SubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchSubs() {
      try {
        const params = statusFilter !== "all" ? { status: statusFilter } : {};
        const res = await subflowService.getSubscriptions(params);
        if (isMounted && res.success) {
          setSubscriptions(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load subscriptions.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchSubs();
    return () => {
      isMounted = false;
    };
  }, [statusFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Subscriptions</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Monitor client recurring contracts, renewals, and billing dates
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {["all", "active", "paused", "cancelled"].map((st) => (
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
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Subscriptions API endpoint: <code className="text-slate-200">GET /api/v1/subscriptions</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading subscriptions..." />
      ) : subscriptions.length === 0 ? (
        <EmptyState
          title="No Subscriptions Recorded"
          description="Subscriptions generated from approved quotations or direct enrollments will appear here."
          developerNote="Model: backend/models/subscription.py | Controller: backend/routes/subscriptions.py"
          icon={Repeat}
          actionText="Create New Subscription"
          onAction={() => alert("Subscriptions Developer can link the new subscription modal/flow here!")}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Subscription #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Start Date</TableHead>
              <TableHead>Next Billing Date</TableHead>
              <TableHead>Recurring Amount</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {subscriptions.map((sub) => (
              <TableRow key={sub.id}>
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {sub.subscription_number}
                </TableCell>
                <TableCell className="font-medium text-white">{sub.customer_name || "Client"}</TableCell>
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
      )}
    </div>
  );
}

export default SubscriptionsPage;
