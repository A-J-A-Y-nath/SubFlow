import React, { useState, useEffect } from "react";
import {
  Repeat,
  DollarSign,
  Receipt,
  AlertTriangle,
  Layers,
  Package,
  PlusCircle,
  ArrowRight,
  TrendingUp,
  Clock,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import dashboardService from "../services/dashboardService";
import StatCard from "../components/common/StatCard";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../components/ui/Table";
import { formatCurrency, formatDate } from "../lib/utils";

export function Dashboard({ onNavigate }) {
  const { user, isAdmin, isCustomer } = useAuth();
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadSummary() {
      try {
        const res = await dashboardService.getSummary();
        if (isMounted && res.success) {
          setSummary(res.data);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Failed to load dashboard metrics.");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    loadSummary();
    return () => {
      isMounted = false;
    };
  }, []);

  if (isLoading) {
    return <LoadingSpinner message="Aggregating subscription metrics..." size="lg" />;
  }

  const metrics = summary?.metrics || {};
  const activeSubs = metrics.active_subscriptions || { count: 0, total: 0 };
  const totalRev = metrics.total_revenue || { amount: 0, currency: "USD" };
  const outstandingInv = metrics.outstanding_invoices || { count: 0, amount: 0, currency: "USD" };
  const overdueInv = metrics.overdue_invoices || { count: 0, amount: 0, currency: "USD" };

  const recentInvoices = summary?.recent_invoices || [];
  const recentSubs = summary?.recent_subscriptions || [];
  const isEmpty = summary?.is_empty;

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-6 rounded-2xl border border-slate-800 bg-gradient-to-r from-slate-900/90 via-slate-900/60 to-brand-950/30 backdrop-blur-md">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold text-white tracking-tight">
              Welcome back, {user?.first_name || (isCustomer ? "Subscriber" : "Team")}
            </h2>
            <Badge variant="brand" className="text-[10px]">
              {isCustomer ? "Customer Portal" : "Make-A-Ton 9.0"}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            {isCustomer
              ? "Manage your active subscription agreements, view statements, and browse upgrade tiers."
              : "SubFlow Core Platform Foundation is active with PostgreSQL on Neon, JWT RBAC, and modular API contracts."}
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          {!isCustomer ? (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onNavigate("/products")}
              >
                <Package className="w-4 h-4 mr-1.5 text-brand-400" />
                Catalog
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onNavigate("/plans")}
              >
                <Layers className="w-4 h-4 mr-1.5" />
                Subscription Plans
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onNavigate("/invoices")}
              >
                <Receipt className="w-4 h-4 mr-1.5 text-brand-400" />
                My Invoices
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => onNavigate("/plans")}
              >
                <Layers className="w-4 h-4 mr-1.5" />
                Browse Plans
              </Button>
            </>
          )}
        </div>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* KPI Stat Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title={isCustomer ? "My Subscriptions" : "Active Subscriptions"}
          value={activeSubs.count}
          icon={Repeat}
          subtext={isCustomer ? "Active recurring agreements" : `of ${activeSubs.total} total subscriptions`}
          badgeText={activeSubs.count > 0 ? (isCustomer ? "Active" : "Operational") : "None Active"}
          accentColor="text-brand-400 bg-brand-500/10 border-brand-500/20"
        />

        <StatCard
          title={isCustomer ? "Total Paid" : "Total Revenue"}
          value={totalRev.amount}
          isCurrency={true}
          currency={totalRev.currency}
          icon={DollarSign}
          subtext={isCustomer ? "Settled across your invoices" : "Settled across all payments"}
          accentColor="text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
        />

        <StatCard
          title={isCustomer ? "Unpaid Invoices" : "Outstanding Invoices"}
          value={outstandingInv.amount}
          isCurrency={true}
          currency={outstandingInv.currency}
          icon={Receipt}
          subtext={`${outstandingInv.count} pending invoice balances`}
          badgeText={outstandingInv.count > 0 ? `${outstandingInv.count} Pending` : "0 Pending"}
          accentColor="text-amber-400 bg-amber-500/10 border-amber-500/20"
        />

        <StatCard
          title="Overdue Invoices"
          value={overdueInv.amount}
          isCurrency={true}
          currency={overdueInv.currency}
          icon={AlertTriangle}
          subtext={`${overdueInv.count} past due date`}
          badgeText={overdueInv.count > 0 ? "Action Required" : "Zero Overdue"}
          accentColor="text-rose-400 bg-rose-500/10 border-rose-500/20"
        />
      </div>

      {/* When the database has zero business records, show clear empty state per requirement 6 */}
      {isEmpty ? (
        <Card className="border-dashed border-slate-800 bg-slate-900/40">
          <EmptyState
            title={isCustomer ? "No Subscriptions Yet" : "Database Ready — Business Modules Standby"}
            description={
              isCustomer
                ? "You do not have any active subscriptions or billing statements yet. Explore our subscription plans to find the right tier for you."
                : "The core platform, authentication, database migrations, and models are fully configured on Neon PostgreSQL. As your teammates implement quotations, subscriptions, and billing workflows, metrics will automatically populate here."
            }
            developerNote={isCustomer ? null : "Shared contracts at docs/api-contracts.md. Seeded accounts & default plans are ready to be utilized."}
            actionText={isCustomer ? "Browse Subscription Plans" : "Browse Seeded Subscription Plans"}
            onAction={() => onNavigate("/plans")}
          />
        </Card>
      ) : (
        /* Operational Activity Sections */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Invoices Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Recent Invoices</CardTitle>
                <CardDescription>Latest customer billing events</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => onNavigate("/invoices")}>
                View All <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </CardHeader>
            <CardContent>
              {recentInvoices.length === 0 ? (
                <EmptyState
                  title="No Invoices Issued Yet"
                  description="When recurring subscription cycles or quotations post invoices, they will display here."
                  developerNote="Module: backend/routes/invoices.py"
                  className="py-6"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Invoice #</TableHead>
                      {!isCustomer ? (
                        <TableHead>Customer</TableHead>
                      ) : (
                        <TableHead>Due Date</TableHead>
                      )}
                      <TableHead>Amount</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentInvoices.map((inv) => (
                      <TableRow key={inv.id}>
                        <TableCell className="font-mono text-xs font-semibold text-brand-400">
                          {inv.invoice_number}
                        </TableCell>
                        {!isCustomer ? (
                          <TableCell className="text-xs">{inv.customer_name || "Client"}</TableCell>
                        ) : (
                          <TableCell className="text-xs text-slate-300">{formatDate(inv.due_date)}</TableCell>
                        )}
                        <TableCell className="text-xs font-medium">
                          {formatCurrency(inv.total_amount, inv.currency)}
                        </TableCell>
                        <TableCell>
                          <Badge status={inv.status}>{inv.status}</Badge>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>

          {/* Recent Subscriptions Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-3">
              <div>
                <CardTitle>Active Subscriptions</CardTitle>
                <CardDescription>Recent recurring customer agreements</CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => onNavigate("/subscriptions")}>
                View All <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </Button>
            </CardHeader>
            <CardContent>
              {recentSubs.length === 0 ? (
                <EmptyState
                  title="No Subscriptions Created Yet"
                  description="Subscriptions created from quotations or plan enrollments will appear here."
                  developerNote="Module: backend/routes/subscriptions.py"
                  className="py-6"
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Subscription #</TableHead>
                      <TableHead>Plan</TableHead>
                      <TableHead>Recurring Amount</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {recentSubs.map((sub) => (
                      <TableRow key={sub.id}>
                        <TableCell className="font-mono text-xs font-semibold text-brand-400">
                          {sub.subscription_number}
                        </TableCell>
                        <TableCell className="text-xs">{sub.plan_name || "Standard"}</TableCell>
                        <TableCell className="text-xs font-medium">
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
            </CardContent>
          </Card>
        </div>
      )}

      {/* Developer Collaboration Hub Banner — internal team only */}
      {!isCustomer && (
        <Card className="border-brand-500/20 bg-gradient-to-r from-brand-950/40 via-slate-900/60 to-slate-900/80">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">
                  Team Collaboration Blueprint (Make-A-Ton 9.0)
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">
                  The database schema, ORM relationships, API conventions, and tests are verified and ready for teammates to drop in features.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onNavigate("/reports")}
              >
                Analytics Preview
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

export default Dashboard;
