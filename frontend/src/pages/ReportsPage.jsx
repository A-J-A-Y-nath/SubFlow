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
  AreaChart,
  Area,
  CartesianGrid
} from "recharts";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Calendar,
  RefreshCw,
  Clock,
  CheckCircle2,
  AlertTriangle,
  PieChart as PieIcon,
  CreditCard
} from "lucide-react";
import subflowService from "../services/subflowService";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import LoadingSpinner from "../components/common/LoadingSpinner";
import EmptyState from "../components/common/EmptyState";
import Alert from "../components/common/Alert";
import { formatCurrency } from "../lib/utils";

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#f43f5e", "#8b5cf6", "#06b6d4"];
const STATUS_COLORS = {
  draft: "#64748b",
  posted: "#3b82f6",
  partial: "#f59e0b",
  paid: "#10b981",
  overdue: "#f43f5e",
  cancelled: "#475569"
};

export function ReportsPage() {
  const [rangeFilter, setRangeFilter] = useState("30d");
  const [analytics, setAnalytics] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchAnalytics = async () => {
    try {
      setError(null);
      const res = await subflowService.getAnalytics({ range: rangeFilter });
      if (res.success) {
        setAnalytics(res.data);
      }
    } catch (err) {
      setError(err.message || "Failed to load financial analytics.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
  }, [rangeFilter]);

  const summary = analytics?.financial_summary || {};
  const revenueTrends = analytics?.revenue_trends || [];
  const planData = analytics?.plan_distribution || [];
  const invoiceData = analytics?.invoice_status_breakdown || [];
  const paymentMethods = analytics?.payment_methods || [];
  const agingData = analytics?.aging_report || {};
  const mrrEstimate = analytics?.mrr_estimate || 0;

  // Format Aging Data for BarChart
  const agingChartData = [
    { name: "Current", amount: agingData.current?.amount || 0, count: agingData.current?.count || 0 },
    { name: "1–30 Days", amount: agingData["1_30"]?.amount || 0, count: agingData["1_30"]?.count || 0 },
    { name: "31–60 Days", amount: agingData["31_60"]?.amount || 0, count: agingData["31_60"]?.count || 0 },
    { name: "61–90 Days", amount: agingData["61_90"]?.amount || 0, count: agingData["61_90"]?.count || 0 },
    { name: "90+ Days", amount: agingData.over_90?.amount || 0, count: agingData.over_90?.count || 0 },
  ];

  const hasData =
    summary.total_revenue > 0 ||
    summary.total_invoiced > 0 ||
    revenueTrends.length > 0 ||
    invoiceData.length > 0;

  return (
    <div className="space-y-6">
      {/* Top Header & Range Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Financial Analytics & Reports</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time accounts receivable, revenue timeline, collection efficiency, and subscriber retention
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Range Selector */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
            {[
              { id: "7d", label: "7 Days" },
              { id: "30d", label: "30 Days" },
              { id: "month", label: "This Month" },
              { id: "year", label: "This Year" },
              { id: "all", label: "All Time" }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setRangeFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  rangeFilter === tab.id
                    ? "bg-brand-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setIsRefreshing(true);
              fetchAnalytics();
            }}
            className="p-2"
            title="Refresh Metrics"
          >
            <RefreshCw className={`w-4 h-4 text-slate-400 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* KPI Cards Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase font-medium tracking-wider">Recorded Revenue</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-black text-emerald-400 mt-1">
            {formatCurrency(summary.total_revenue || 0)}
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">
            From {summary.completed_payments_count || 0} completed receipts
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase font-medium tracking-wider">Estimated MRR</span>
            <TrendingUp className="w-4 h-4 text-brand-400" />
          </div>
          <p className="text-2xl font-black text-brand-400 mt-1">
            {formatCurrency(mrrEstimate)}
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">
            {summary.active_subscriptions_count || 0} active subscriptions
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase font-medium tracking-wider">Outstanding Receivables</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-black text-amber-400 mt-1">
            {formatCurrency(summary.outstanding_amount || 0)}
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">
            {summary.outstanding_count || 0} unpaid balances
          </span>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="uppercase font-medium tracking-wider">Collection Efficiency</span>
            <CheckCircle2 className="w-4 h-4 text-white" />
          </div>
          <p className="text-2xl font-black text-white mt-1">
            {summary.collection_rate_percent || 0}%
          </p>
          <span className="text-[10px] text-slate-500 mt-0.5 block">
            Overdue: {formatCurrency(summary.overdue_amount || 0)}
          </span>
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner message="Calculating financial models & Recharts series..." size="lg" />
      ) : !hasData ? (
        <EmptyState
          title="Awaiting Operational Transactions"
          description="Analytical reporting charts will automatically render revenue timelines, aging buckets, and receivables breakdown once records are posted."
          icon={BarChart3}
        />
      ) : (
        <div className="space-y-6">
          {/* Revenue Over Time AreaChart */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-emerald-400" />
                    Revenue Collections Over Time
                  </CardTitle>
                  <CardDescription>Daily/monthly volume of actual settled customer payments</CardDescription>
                </div>
                <Badge variant="success">Settled Receipts</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="h-72 w-full pt-4">
                {revenueTrends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={revenueTrends} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#020617",
                          borderColor: "#1e293b",
                          borderRadius: "8px",
                          fontSize: "12px",
                          color: "#fff"
                        }}
                        formatter={(val) => [`$${val.toFixed(2)}`, "Revenue"]}
                      />
                      <Area
                        type="monotone"
                        dataKey="revenue"
                        stroke="#10b981"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#revenueGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
                    No payment transactions recorded during this period.
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Middle Row: Invoices Breakdown & Aging Analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Invoices Status Breakdown (PieChart) */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                  <PieIcon className="w-4 h-4 text-brand-400" />
                  Invoicing Health & Lifecycle Breakdown
                </CardTitle>
                <CardDescription>Accounts receivable distribution across billing statuses</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 w-full">
                  {invoiceData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={invoiceData}
                          dataKey="count"
                          nameKey="label"
                          cx="50%"
                          cy="50%"
                          outerRadius={80}
                          innerRadius={45}
                          paddingAngle={3}
                        >
                          {invoiceData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={STATUS_COLORS[entry.status] || CHART_COLORS[index % CHART_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#020617",
                            borderColor: "#1e293b",
                            borderRadius: "8px",
                            fontSize: "12px",
                            color: "#fff"
                          }}
                          formatter={(count, name, entry) => [
                            `${count} statements ($${entry.payload.total_amount?.toFixed(2) || 0})`,
                            name
                          ]}
                        />
                        <Legend
                          verticalAlign="bottom"
                          iconType="circle"
                          wrapperStyle={{ fontSize: "11px", paddingTop: "10px" }}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
                      No invoices recorded yet.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Receivables Aging Analysis (BarChart) */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  Receivables Aging Analysis
                </CardTitle>
                <CardDescription>Overdue invoice balances grouped by aging buckets</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={agingChartData} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} interval={0} />
                      <YAxis stroke="#64748b" fontSize={10} tickLine={false} tickFormatter={(v) => `$${v}`} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: "#020617",
                          borderColor: "#1e293b",
                          borderRadius: "8px",
                          fontSize: "12px",
                          color: "#fff"
                        }}
                        formatter={(val, name, entry) => [
                          `$${val.toFixed(2)} (${entry.payload.count} invoices)`,
                          "Outstanding"
                        ]}
                      />
                      <Bar dataKey="amount" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Bottom Row: Plan Distribution & Payment Methods */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Subscriptions by Plan (BarChart) */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-brand-400" />
                  Active Subscriptions by Plan Tier
                </CardTitle>
                <CardDescription>Subscriber base distribution across subscription packages</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-60 w-full">
                  {planData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={planData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="plan" stroke="#64748b" fontSize={11} tickLine={false} interval={0} />
                        <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#020617",
                            borderColor: "#1e293b",
                            borderRadius: "8px",
                            fontSize: "12px",
                            color: "#fff"
                          }}
                        />
                        <Bar dataKey="subscriptions" fill="#6366f1" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
                      No active subscriptions found.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Payment Methods (BarChart) */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-bold text-white flex items-center gap-2">
                  <CreditCard className="w-4 h-4 text-emerald-400" />
                  Collected Revenue by Payment Method
                </CardTitle>
                <CardDescription>Volume distribution across settlement payment gateways</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-60 w-full">
                  {paymentMethods.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={paymentMethods} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis dataKey="label" stroke="#64748b" fontSize={11} tickLine={false} interval={0} />
                        <YAxis stroke="#64748b" fontSize={11} tickLine={false} tickFormatter={(v) => `$${v}`} />
                        <Tooltip
                          contentStyle={{
                            backgroundColor: "#020617",
                            borderColor: "#1e293b",
                            borderRadius: "8px",
                            fontSize: "12px",
                            color: "#fff"
                          }}
                          formatter={(val, name, entry) => [
                            `$${val.toFixed(2)} (${entry.payload.count} transactions)`,
                            "Revenue"
                          ]}
                        />
                        <Bar dataKey="total_amount" fill="#10b981" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="flex h-full items-center justify-center text-xs text-slate-500 italic">
                      No completed payments recorded yet.
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportsPage;
