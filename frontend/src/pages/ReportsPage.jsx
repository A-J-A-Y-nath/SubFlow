import React, { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { BarChart3, TrendingUp, DollarSign } from "lucide-react";
import dashboardService from "../services/dashboardService";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import LoadingSpinner from "../components/common/LoadingSpinner";
import EmptyState from "../components/common/EmptyState";
import Alert from "../components/common/Alert";
import { formatCurrency } from "../lib/utils";

const COLORS = ["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#06b6d4"];

export function ReportsPage() {
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchAnalytics() {
      try {
        const res = await dashboardService.getAnalytics();
        if (isMounted && res.success) {
          setAnalytics(res.data);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load analytics.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchAnalytics();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return <LoadingSpinner message="Generating analytical charts..." size="lg" />;
  }

  const planData = analytics?.plan_distribution || [];
  const invoiceData = analytics?.invoice_status_breakdown || [];
  const mrrEstimate = analytics?.mrr_estimate || 0;

  const hasData = planData.some((p) => p.subscriptions > 0) || invoiceData.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Analytics & Financial Reports</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Aggregated revenue trends, plan distributions, and receivables performance
          </p>
        </div>

        <div className="flex items-center gap-2 p-3 rounded-xl bg-slate-900 border border-slate-800">
          <div className="p-2 rounded-lg bg-brand-500/10 text-brand-400 border border-brand-500/20">
            <TrendingUp className="w-4 h-4" />
          </div>
          <div>
            <p className="text-[10px] uppercase font-semibold text-slate-400">Estimated MRR</p>
            <p className="text-sm font-bold text-white">{formatCurrency(mrrEstimate)}</p>
          </div>
        </div>
      </div>

      {/* Developer note */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Analytics endpoint: <code className="text-slate-200">GET /api/v1/reports/analytics</code> (Recharts integration)
        </span>
        <Badge variant="brand" className="text-[10px]">Recharts Configured</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {!hasData ? (
        <EmptyState
          title="Awaiting Operational Transactions"
          description="Analytical reporting charts will automatically render subscription distributions and invoice metrics once data is posted through the respective modules."
          developerNote="Model: backend/routes/reports.py | Charts: Recharts ResponsiveContainer"
          icon={BarChart3}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Subscriptions by Plan (Bar Chart) */}
          <Card>
            <CardHeader>
              <CardTitle>Subscriptions by Plan Tier</CardTitle>
              <CardDescription>Active subscription distribution across product tiers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={planData} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                    <XAxis
                      dataKey="plan"
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      interval={0}
                    />
                    <YAxis
                      stroke="#64748b"
                      fontSize={11}
                      tickLine={false}
                      allowDecimals={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="subscriptions" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Invoices by Status (Pie Chart) */}
          <Card>
            <CardHeader>
              <CardTitle>Invoices Breakdown by Status</CardTitle>
              <CardDescription>Receivables health across billing lifecycle</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={invoiceData}
                      dataKey="count"
                      nameKey="status"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                      labelLine={false}
                    >
                      {invoiceData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#0f172a",
                        borderColor: "#334155",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

export default ReportsPage;
