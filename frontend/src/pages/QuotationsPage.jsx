import React, { useState, useEffect } from "react";
import { FileText, Plus, Search } from "lucide-react";
import subflowService from "../services/subflowService";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

export function QuotationsPage() {
  const [quotations, setQuotations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchQuotes() {
      try {
        const params = statusFilter !== "all" ? { status: statusFilter } : {};
        const res = await subflowService.getQuotations(params);
        if (isMounted && res.success) {
          setQuotations(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load quotations.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchQuotes();
    return () => {
      isMounted = false;
    };
  }, [statusFilter]);

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

        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {["all", "draft", "sent", "approved", "expired"].map((st) => (
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
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Quotations API endpoint: <code className="text-slate-200">GET /api/v1/quotations</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading quotations..." />
      ) : quotations.length === 0 ? (
        <EmptyState
          title="No Quotations in Pipeline"
          description="Create sales quotations with tailored discount lines to send to prospective clients."
          developerNote="Model: backend/models/quotation.py | Controller: backend/routes/quotations.py"
          icon={FileText}
          actionText="Draft Quotation"
          onAction={() => alert("Quotations Developer will link the proposal builder modal here!")}
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Quotation #</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Plan</TableHead>
              <TableHead>Issue Date</TableHead>
              <TableHead>Valid Until</TableHead>
              <TableHead>Total Amount</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {quotations.map((q) => (
              <TableRow key={q.id}>
                <TableCell className="font-mono text-xs font-semibold text-brand-400">
                  {q.quotation_number}
                </TableCell>
                <TableCell className="font-medium text-white">{q.customer_name || "Client"}</TableCell>
                <TableCell className="text-xs text-slate-300">{q.plan_name || "Custom Tier"}</TableCell>
                <TableCell className="text-xs text-slate-400">{formatDate(q.issue_date)}</TableCell>
                <TableCell className="text-xs text-slate-300">{formatDate(q.valid_until)}</TableCell>
                <TableCell className="font-semibold text-slate-200">
                  {formatCurrency(q.total_amount, q.currency)}
                </TableCell>
                <TableCell>
                  <Badge status={q.status}>{q.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

export default QuotationsPage;
