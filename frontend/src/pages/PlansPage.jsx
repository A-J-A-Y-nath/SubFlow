import React, { useState, useEffect, useCallback } from "react";
import {
  Layers,
  Check,
  Plus,
  Clock,
  Search,
  Pencil,
  Trash2,
  Calendar,
  DollarSign,
  AlertTriangle,
  RefreshCw,
  Repeat,
  CheckCircle2,
  XCircle,
  Hash,
} from "lucide-react";
import subflowService from "../services/subflowService";
import { useAuth } from "../hooks/useAuth";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import Input from "../components/ui/Input";
import Modal from "../components/ui/Modal";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { formatCurrency, formatDate } from "../lib/utils";

const INITIAL_PLAN_FORM = {
  name: "",
  code: "",
  description: "",
  billing_interval: "monthly",
  billing_interval_count: 1,
  base_price: "",
  setup_fee: "0.00",
  currency: "USD",
  trial_days: "0",
  min_quantity: "1",
  available_from: "",
  available_until: "",
  auto_renew: true,
  is_active: true,
  features: "",
};

export function PlansPage() {
  const { isAdmin, isStaff } = useAuth();
  const canManage = isAdmin || isStaff;

  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [intervalFilter, setIntervalFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState(null);

  // Modal states
  const [isPlanModalOpen, setIsPlanModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState(null);
  const [planForm, setPlanForm] = useState(INITIAL_PLAN_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Deletion modal
  const [deletingPlan, setDeletingPlan] = useState(null);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const loadPlanData = useCallback(async () => {
    try {
      const params = {};
      if (intervalFilter !== "all") params.billing_interval = intervalFilter;
      if (statusFilter === "active") params.is_active = true;
      if (statusFilter === "inactive") params.is_active = false;
      if (search.trim()) params.search = search.trim();

      const res = await subflowService.getPlans(params);
      if (res.success) {
        setPlans(res.data?.items || []);
      }
    } catch (err) {
      setError(err.message || "Failed to load plans.");
    } finally {
      setIsLoading(false);
    }
  }, [intervalFilter, statusFilter, search]);

  useEffect(() => {
    let isMounted = true;
    async function init() {
      try {
        const params = {};
        if (intervalFilter !== "all") params.billing_interval = intervalFilter;
        if (statusFilter === "active") params.is_active = true;
        if (statusFilter === "inactive") params.is_active = false;
        if (search.trim()) params.search = search.trim();

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

    init();
    return () => {
      isMounted = false;
    };
  }, [intervalFilter, statusFilter, search]);

  const refreshPlans = () => {
    setIsLoading(true);
    loadPlanData();
  };

  // Form Handlers
  const handleOpenCreatePlan = () => {
    setEditingPlan(null);
    setPlanForm(INITIAL_PLAN_FORM);
    setFormErrors({});
    setIsPlanModalOpen(true);
  };

  const handleOpenEditPlan = (plan) => {
    setEditingPlan(plan);
    setPlanForm({
      name: plan.name,
      code: plan.code,
      description: plan.description || "",
      billing_interval: plan.billing_interval || "monthly",
      billing_interval_count: plan.billing_interval_count || 1,
      base_price: plan.base_price,
      setup_fee: plan.setup_fee || "0.00",
      currency: plan.currency || "USD",
      trial_days: plan.trial_days !== undefined ? plan.trial_days.toString() : "0",
      min_quantity: plan.min_quantity !== undefined ? plan.min_quantity.toString() : "1",
      available_from: plan.available_from || "",
      available_until: plan.available_until || "",
      auto_renew: plan.auto_renew !== undefined ? plan.auto_renew : true,
      is_active: plan.is_active,
      features: Array.isArray(plan.features) ? plan.features.join("\n") : "",
    });
    setFormErrors({});
    setIsPlanModalOpen(true);
  };

  const validatePlanForm = () => {
    const errors = {};
    if (!planForm.name.trim()) errors.name = "Plan name is required";
    if (!planForm.code.trim()) errors.code = "Plan code is required";
    if (planForm.base_price === "" || isNaN(planForm.base_price)) {
      errors.base_price = "Base price must be a valid number";
    } else if (parseFloat(planForm.base_price) < 0) {
      errors.base_price = "Base price cannot be negative";
    }

    if (planForm.setup_fee !== "" && (isNaN(planForm.setup_fee) || parseFloat(planForm.setup_fee) < 0)) {
      errors.setup_fee = "Setup fee must be a valid non-negative number";
    }

    const minQty = parseInt(planForm.min_quantity, 10);
    if (isNaN(minQty) || minQty < 1) {
      errors.min_quantity = "Minimum subscription quantity must be at least 1";
    }

    const trialDays = parseInt(planForm.trial_days, 10);
    if (isNaN(trialDays) || trialDays < 0) {
      errors.trial_days = "Trial days cannot be negative";
    }

    if (planForm.available_from && planForm.available_until) {
      if (planForm.available_until < planForm.available_from) {
        errors.available_until = "Available-until date cannot be earlier than available-from date";
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSavePlan = async (e) => {
    e.preventDefault();
    if (!validatePlanForm()) return;

    setIsSubmitting(true);
    setError(null);
    try {
      const featuresList = planForm.features
        .split("\n")
        .map((f) => f.trim())
        .filter((f) => f.length > 0);

      const payload = {
        name: planForm.name.trim(),
        code: planForm.code.trim().toUpperCase(),
        description: planForm.description.trim(),
        billing_interval: planForm.billing_interval,
        billing_interval_count: parseInt(planForm.billing_interval_count, 10) || 1,
        base_price: parseFloat(planForm.base_price),
        setup_fee: parseFloat(planForm.setup_fee || 0),
        currency: planForm.currency,
        trial_days: parseInt(planForm.trial_days, 10) || 0,
        min_quantity: parseInt(planForm.min_quantity, 10) || 1,
        available_from: planForm.available_from || null,
        available_until: planForm.available_until || null,
        auto_renew: !!planForm.auto_renew,
        is_active: !!planForm.is_active,
        features: featuresList,
      };

      if (editingPlan) {
        await subflowService.updatePlan(editingPlan.id, payload);
        setSuccessMessage(`Plan '${payload.name}' updated successfully.`);
      } else {
        await subflowService.createPlan(payload);
        setSuccessMessage(`Plan '${payload.name}' created successfully.`);
      }

      setIsPlanModalOpen(false);
      refreshPlans();
    } catch (err) {
      setError(err.message || "Failed to save subscription plan.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTogglePlanStatus = async (plan) => {
    try {
      await subflowService.togglePlanStatus(plan.id, !plan.is_active);
      setSuccessMessage(`Plan '${plan.name}' ${!plan.is_active ? "activated" : "deactivated"}.`);
      refreshPlans();
    } catch (err) {
      setError(err.message || "Failed to change plan status.");
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingPlan) return;
    setIsSubmitting(true);
    try {
      await subflowService.deletePlan(deletingPlan.id);
      setSuccessMessage(`Plan '${deletingPlan.name}' deleted successfully.`);
      setIsDeleteModalOpen(false);
      setDeletingPlan(null);
      refreshPlans();
    } catch (err) {
      setError(err.message || "Deletion failed. Plan may be in use by active subscriptions or quotations.");
      setIsDeleteModalOpen(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-brand-400" />
            Subscription Plans
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure recurring pricing tiers, billing cadences, trial periods, and feature packages
          </p>
        </div>

        {canManage && (
          <div className="flex items-center gap-2">
            <Button variant="primary" size="sm" onClick={handleOpenCreatePlan}>
              <Plus className="w-4 h-4 mr-1.5" />
              Create Plan
            </Button>
          </div>
        )}
      </div>

      {/* Notifications */}
      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMessage && <Alert type="success" message={successMessage} onClose={() => setSuccessMessage(null)} />}

      {/* Filter and Cadence Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/60 border border-slate-800">
        <div className="max-w-xs w-full">
          <Input
            placeholder="Search plans by name or code..."
            icon={Search}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Cadence Switcher */}
          <div className="flex items-center gap-1 p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs overflow-x-auto">
            {["all", "daily", "weekly", "monthly", "quarterly", "yearly"].map((cycle) => (
              <button
                key={cycle}
                onClick={() => setIntervalFilter(cycle)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize whitespace-nowrap transition-all ${
                  intervalFilter === cycle
                    ? "bg-brand-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {cycle === "all" ? "All Cadences" : cycle}
              </button>
            ))}
          </div>

          {/* Status Filter for Staff/Admin */}
          {canManage && (
            <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-900 border border-slate-800 text-xs">
              {["all", "active", "inactive"].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-2.5 py-1 rounded capitalize transition-all ${
                    statusFilter === s ? "bg-slate-700 text-white font-medium" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {s === "all" ? "All Status" : s}
                </button>
              ))}
            </div>
          )}

          <Button variant="ghost" size="sm" onClick={refreshPlans} title="Refresh plans">
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Plan Grid */}
      {isLoading ? (
        <LoadingSpinner message="Loading subscription plans..." />
      ) : plans.length === 0 ? (
        <EmptyState
          title="No Subscription Plans Found"
          description={
            search || intervalFilter !== "all" || statusFilter !== "all"
              ? "No plans match your current filter parameters. Try clearing your filters."
              : "No subscription plans have been defined yet. Click 'Create Plan' to get started."
          }
          icon={Layers}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plans.map((plan, index) => {
            const isFeatured = index === 1; // Highlight second tier if available
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
                  {/* Top line: Name & Code */}
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="text-lg font-bold text-white">{plan.name}</h3>
                    <div className="flex items-center gap-1.5">
                      <Badge variant="brand" className="text-[10px] font-mono">
                        {plan.code}
                      </Badge>
                      <Badge status={plan.is_active ? "active" : "inactive"}>
                        {plan.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>
                  </div>

                  <p className="text-xs text-slate-400 mt-2 leading-relaxed min-h-[36px]">
                    {plan.description || "Full-featured subscription tier tailored for growth."}
                  </p>

                  {/* Price Header */}
                  <div className="mt-5 pb-4 border-b border-slate-800">
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-3xl font-extrabold text-white">
                        {formatCurrency(plan.base_price, plan.currency)}
                      </span>
                      <span className="text-xs text-slate-400 capitalize">
                        /{plan.billing_interval_count > 1 ? `${plan.billing_interval_count} ` : ""}
                        {plan.billing_interval}
                      </span>
                    </div>

                    {plan.setup_fee > 0 && (
                      <p className="text-[11px] text-slate-400 mt-1">
                        + {formatCurrency(plan.setup_fee, plan.currency)} one-time setup fee
                      </p>
                    )}
                  </div>

                  {/* Meta Badges */}
                  <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
                    {plan.trial_days > 0 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/15 text-emerald-400 font-medium border border-emerald-500/20">
                        <Clock className="w-3 h-3" />
                        {plan.trial_days}-Day Free Trial
                      </span>
                    )}

                    {plan.min_quantity > 1 && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                        <Hash className="w-3 h-3 text-brand-400" />
                        Min. {plan.min_quantity} units
                      </span>
                    )}

                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                      <Repeat className="w-3 h-3 text-brand-400" />
                      {plan.auto_renew ? "Auto-renew On" : "Manual Renewal"}
                    </span>

                    {(plan.available_from || plan.available_until) && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700">
                        <Calendar className="w-3 h-3" />
                        {plan.available_from ? formatDate(plan.available_from) : "Open"} –{" "}
                        {plan.available_until ? formatDate(plan.available_until) : "Ongoing"}
                      </span>
                    )}
                  </div>

                  {/* Features List */}
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
                      <p className="text-xs text-slate-500 italic">Standard features package included.</p>
                    )}
                  </div>
                </div>

                {/* Management Toolbar or Action */}
                <div className="mt-8 pt-4 border-t border-slate-800/80">
                  {canManage ? (
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-1">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleOpenEditPlan(plan)}
                          title="Edit Plan"
                        >
                          <Pencil className="w-3.5 h-3.5 mr-1" />
                          Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleTogglePlanStatus(plan)}
                          title={plan.is_active ? "Deactivate" : "Activate"}
                          className={plan.is_active ? "hover:text-amber-400" : "hover:text-emerald-400"}
                        >
                          {plan.is_active ? <XCircle className="w-3.5 h-3.5" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                        </Button>
                      </div>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          setDeletingPlan(plan);
                          setIsDeleteModalOpen(true);
                        }}
                        title="Delete Plan"
                        className="hover:text-rose-400"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant={isFeatured ? "primary" : "secondary"}
                      className="w-full justify-center"
                      onClick={() => alert(`Subscribing to ${plan.name} will be connected in Subscriptions module!`)}
                    >
                      Select {plan.name}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ====================================================================== */}
      {/* Create / Edit Plan Modal */}
      {/* ====================================================================== */}
      <Modal
        isOpen={isPlanModalOpen}
        onClose={() => setIsPlanModalOpen(false)}
        title={editingPlan ? "Edit Subscription Plan" : "Create Subscription Plan"}
        description={
          editingPlan
            ? "Update pricing, billing interval, quantity requirements, and feature set."
            : "Define a recurring pricing tier with trial periods, minimum quantity limits, and billing intervals."
        }
        maxWidth="max-w-2xl"
      >
        <form onSubmit={handleSavePlan} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Plan Name *"
              placeholder="e.g. Professional Plan"
              value={planForm.name}
              onChange={(e) => setPlanForm({ ...planForm, name: e.target.value })}
              error={formErrors.name}
            />
            <Input
              label="Plan Code *"
              placeholder="e.g. PLAN-PRO-MO"
              value={planForm.code}
              onChange={(e) => setPlanForm({ ...planForm, code: e.target.value.toUpperCase() })}
              error={formErrors.code}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Billing Cadence *
              </label>
              <select
                value={planForm.billing_interval}
                onChange={(e) => setPlanForm({ ...planForm, billing_interval: e.target.value })}
                className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
              </select>
            </div>

            <Input
              label="Interval Count *"
              type="number"
              min="1"
              value={planForm.billing_interval_count}
              onChange={(e) => setPlanForm({ ...planForm, billing_interval_count: e.target.value })}
            />

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
                Currency
              </label>
              <select
                value={planForm.currency}
                onChange={(e) => setPlanForm({ ...planForm, currency: e.target.value })}
                className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
              >
                <option value="USD">USD ($)</option>
                <option value="INR">INR (₹)</option>
                <option value="EUR">EUR (€)</option>
                <option value="GBP">GBP (£)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Base Price per Interval *"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              icon={DollarSign}
              value={planForm.base_price}
              onChange={(e) => setPlanForm({ ...planForm, base_price: e.target.value })}
              error={formErrors.base_price}
            />

            <Input
              label="One-Time Setup Fee"
              type="number"
              step="0.01"
              min="0"
              placeholder="0.00"
              icon={DollarSign}
              value={planForm.setup_fee}
              onChange={(e) => setPlanForm({ ...planForm, setup_fee: e.target.value })}
              error={formErrors.setup_fee}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Free Trial Period (Days)"
              type="number"
              min="0"
              placeholder="0"
              icon={Clock}
              value={planForm.trial_days}
              onChange={(e) => setPlanForm({ ...planForm, trial_days: e.target.value })}
              error={formErrors.trial_days}
            />

            <Input
              label="Minimum Subscription Quantity"
              type="number"
              min="1"
              placeholder="1"
              icon={Hash}
              value={planForm.min_quantity}
              onChange={(e) => setPlanForm({ ...planForm, min_quantity: e.target.value })}
              error={formErrors.min_quantity}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Input
              label="Available From Date"
              type="date"
              value={planForm.available_from}
              onChange={(e) => setPlanForm({ ...planForm, available_from: e.target.value })}
            />

            <Input
              label="Available Until Date"
              type="date"
              value={planForm.available_until}
              onChange={(e) => setPlanForm({ ...planForm, available_until: e.target.value })}
              error={formErrors.available_until}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Plan Features (One feature per line)
            </label>
            <textarea
              rows={4}
              placeholder="Up to 25 Users&#10;Advanced Analytics&#10;Priority Support&#10;Unlimited Projects"
              value={planForm.features}
              onChange={(e) => setPlanForm({ ...planForm, features: e.target.value })}
              className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 p-3 text-sm text-slate-100 placeholder-slate-500 font-mono text-xs focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300 mb-1.5">
              Description
            </label>
            <textarea
              rows={2}
              placeholder="Brief summary of target audience and tier capabilities..."
              value={planForm.description}
              onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
              className="w-full rounded-lg bg-slate-900/90 border border-slate-700/80 p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div className="flex items-center gap-6 pt-2 border-t border-slate-800">
            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-300 font-medium">
              <input
                type="checkbox"
                checked={planForm.auto_renew}
                onChange={(e) => setPlanForm({ ...planForm, auto_renew: e.target.checked })}
                className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 w-4 h-4"
              />
              Auto-Renew Subscriptions by Default
            </label>

            <label className="flex items-center gap-2 cursor-pointer select-none text-xs text-slate-300 font-medium">
              <input
                type="checkbox"
                checked={planForm.is_active}
                onChange={(e) => setPlanForm({ ...planForm, is_active: e.target.checked })}
                className="rounded border-slate-700 bg-slate-900 text-brand-600 focus:ring-brand-500 w-4 h-4"
              />
              Active (Visible for selection)
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsPlanModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" isLoading={isSubmitting}>
              {editingPlan ? "Save Changes" : "Create Plan"}
            </Button>
          </div>
        </form>
      </Modal>

      {/* ====================================================================== */}
      {/* Confirmation Dialog for Plan Deletion */}
      {/* ====================================================================== */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title={`Delete Plan: ${deletingPlan?.name}?`}
        description="This action cannot be undone. Plans referenced by existing subscriptions or quotations cannot be deleted and must be deactivated instead."
        maxWidth="max-w-md"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
            <div>
              <p className="font-semibold text-rose-200">Confirmation Required:</p>
              <p className="mt-0.5">
                Are you sure you want to delete plan{" "}
                <code className="font-mono text-rose-100">{deletingPlan?.code}</code>?
              </p>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setIsDeleteModalOpen(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={handleConfirmDelete}
              isLoading={isSubmitting}
            >
              Yes, Delete Plan
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

export default PlansPage;
