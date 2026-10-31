import React, { useState, useEffect } from "react";
import { Layers, Check, Plus, Clock, Sparkles } from "lucide-react";
import subflowService from "../services/subflowService";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency } from "../lib/utils";

export function PlansPage() {
  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [intervalFilter, setIntervalFilter] = useState("all");
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchPlans() {
      try {
        const params = intervalFilter !== "all" ? { billing_interval: intervalFilter } : {};
        const res = await subflowService.getPlans(params);
        if (isMounted && res.success) {
          setPlans(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load plans.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchPlans();
    return () => {
      isMounted = false;
    };
  }, [intervalFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Subscription Plans</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure pricing tiers, billing cadences, trial periods, and feature packages
          </p>
        </div>

        {/* Cadence Switcher */}
        <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800">
          {["all", "monthly", "yearly"].map((cycle) => (
            <button
              key={cycle}
              onClick={() => setIntervalFilter(cycle)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                intervalFilter === cycle
                  ? "bg-brand-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {cycle === "all" ? "All Cadences" : cycle}
            </button>
          ))}
        </div>
      </div>

      {/* Developer notice */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Plans API endpoint: <code className="text-slate-200">GET /api/v1/plans</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Plan Grid */}
      {isLoading ? (
        <LoadingSpinner message="Loading subscription plans..." />
      ) : plans.length === 0 ? (
        <EmptyState
          title="No Subscription Plans Defined"
          description="Create plans or run 'flask seed' on the backend to load default Starter, Pro, and Enterprise tiers."
          developerNote="Model: backend/models/plan.py | Controller: backend/routes/plans.py"
          icon={Layers}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {plans.map((plan, index) => {
            const isFeatured = index === 1; // Highlight middle tier (Pro)
            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl border p-6 flex flex-col justify-between backdrop-blur-md transition-all duration-200 hover:-translate-y-1 ${
                  isFeatured
                    ? "border-brand-500 bg-gradient-to-b from-brand-950/40 via-slate-900/90 to-slate-900/90 shadow-2xl shadow-brand-500/10"
                    : "border-slate-800 bg-slate-900/70 hover:border-slate-700"
                }`}
              >
                {isFeatured && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-brand-600 text-white text-[10px] font-bold uppercase tracking-wider shadow">
                    Most Popular
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                    <Badge variant="brand" className="text-[10px] font-mono">
                      {plan.code}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-2 leading-relaxed min-h-[36px]">
                    {plan.description || "Full-featured subscription tier tailored for scale."}
                  </p>

                  <div className="mt-5 pb-5 border-b border-slate-800 flex items-baseline gap-1.5">
                    <span className="text-3xl font-extrabold text-white">
                      {formatCurrency(plan.base_price, plan.currency)}
                    </span>
                    <span className="text-xs text-slate-400">/{plan.billing_interval}</span>
                  </div>

                  {plan.trial_days > 0 && (
                    <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{plan.trial_days}-Day Free Trial Included</span>
                    </div>
                  )}

                  <div className="mt-5 space-y-2.5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                      Features Included:
                    </p>
                    {Array.isArray(plan.features) && plan.features.length > 0 ? (
                      plan.features.map((feat, i) => (
                        <div key={i} className="flex items-start gap-2 text-xs text-slate-300">
                          <Check className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                          <span>{feat}</span>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-slate-500 italic">Standard tier features included.</p>
                    )}
                  </div>
                </div>

                <div className="mt-8 pt-4 border-t border-slate-800/80">
                  <Button
                    variant={isFeatured ? "primary" : "secondary"}
                    className="w-full justify-center"
                    onClick={() => alert(`Subscribing to ${plan.name} will be connected by Subscriptions developer!`)}
                  >
                    Select {plan.name}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PlansPage;
