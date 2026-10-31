import React, { useState, useEffect } from "react";
import { Plus, Trash2, Package, Calendar, User } from "lucide-react";
import Modal from "../../components/ui/Modal";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Alert from "../../components/common/Alert";
import subflowService from "../../services/subflowService";

const emptyLine = () => ({ product_id: "", description: "", quantity: 1, unit_price: "", discount_percent: 0 });

export function CreateSubscriptionModal({ isOpen, onClose, onSuccess }) {
  const [plans, setPlans] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    plan_id: "",
    customer_id: "",
    start_date: new Date().toISOString().slice(0, 10),
    auto_renew: true,
  });
  const [lines, setLines] = useState([emptyLine()]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load selects on modal open
  useEffect(() => {
    if (!isOpen) return;
    Promise.all([
      subflowService.getPlans({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
      subflowService.getCustomers({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
      subflowService.getProducts({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
    ]).then(([plansRes, custsRes, prodsRes]) => {
      const pItems = Array.isArray(plansRes?.data) ? plansRes.data : plansRes?.data?.items || [];
      const cItems = Array.isArray(custsRes?.data) ? custsRes.data : custsRes?.data?.items || [];
      const prItems = Array.isArray(prodsRes?.data) ? prodsRes.data : prodsRes?.data?.items || [];
      setPlans(pItems);
      setCustomers(cItems);
      setProducts(prItems);
    });
  }, [isOpen]);

  // Selected plan object
  const selectedPlan = plans.find((p) => String(p.id) === String(form.plan_id));

  // When plan changes, populate base price, description, interval, and auto-renew
  const handlePlanChange = (selectedPlanId) => {
    const plan = plans.find((p) => String(p.id) === String(selectedPlanId));
    setForm((prev) => ({
      ...prev,
      plan_id: selectedPlanId,
      auto_renew: plan && plan.auto_renew !== undefined ? Boolean(plan.auto_renew) : prev.auto_renew,
    }));

    if (plan) {
      const planPrice = parseFloat(plan.base_price) || 0;
      const planDesc = `${plan.name} (${plan.billing_interval || "monthly"})`;

      // Auto-assign first product if line doesn't have one
      let defaultProdId = "";
      if (products.length > 0) {
        const matched =
          products.find(
            (pr) =>
              pr.name?.toLowerCase().includes(plan.name?.toLowerCase()) ||
              pr.sku?.toLowerCase().includes(plan.code?.toLowerCase())
          ) || products[0];
        defaultProdId = String(matched.id);
      }

      setLines((prev) => {
        if (prev.length <= 1) {
          return [
            {
              product_id: defaultProdId || prev[0]?.product_id || "",
              description: planDesc,
              quantity: plan.min_quantity || 1,
              unit_price: planPrice,
              discount_percent: 0,
            },
          ];
        }
        return prev.map((l, i) =>
          i === 0
            ? {
                ...l,
                product_id: l.product_id || defaultProdId,
                description: l.description || planDesc,
                unit_price: planPrice,
              }
            : l
        );
      });
    }
  };

  // Auto-fill description & price from selected product if line product changes
  const handleLineProductChange = (idx, productId) => {
    const prod = products.find((p) => String(p.id) === String(productId));
    setLines((prev) =>
      prev.map((l, i) =>
        i === idx
          ? {
              ...l,
              product_id: productId,
              description: prod?.name || l.description,
              unit_price: prod?.default_price !== undefined ? prod.default_price : l.unit_price,
            }
          : l
      )
    );
  };

  const updateLine = (idx, field, value) => {
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));
  };

  const addLine = () => setLines((prev) => [...prev, emptyLine()]);
  const removeLine = (idx) => setLines((prev) => prev.filter((_, i) => i !== idx));

  const recurringTotal = lines.reduce((sum, l) => {
    const qty = parseFloat(l.quantity) || 0;
    const price = parseFloat(l.unit_price) || 0;
    const disc = parseFloat(l.discount_percent) || 0;
    return sum + qty * price * (1 - disc / 100);
  }, 0);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const res = await subflowService.createSubscription({
        ...form,
        plan_id: parseInt(form.plan_id),
        customer_id: parseInt(form.customer_id),
        lines: lines.map((l) => ({
          product_id: parseInt(l.product_id),
          description: l.description,
          quantity: parseFloat(l.quantity),
          unit_price: parseFloat(l.unit_price),
          discount_percent: parseFloat(l.discount_percent) || 0,
        })),
      });
      onSuccess?.(res.data);
      onClose();
      setLines([emptyLine()]);
      setForm({ plan_id: "", customer_id: "", start_date: new Date().toISOString().slice(0, 10), auto_renew: true });
    } catch (err) {
      setError(err.message || "Failed to create subscription.");
    } finally {
      setIsLoading(false);
    }
  };

  const selectClass =
    "w-full rounded-lg bg-slate-900/90 border border-slate-700/80 px-3.5 py-2.5 text-sm text-slate-100 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500";

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="New Subscription"
      description="Create a subscription by selecting a customer, plan, and defining line items."
      maxWidth="max-w-3xl"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        {/* Customer + Plan */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Customer *
            </label>
            <select
              className={selectClass}
              value={form.customer_id}
              onChange={(e) => setForm({ ...form, customer_id: e.target.value })}
              required
            >
              <option value="">Select customer…</option>
              {customers.map((c) => {
                const label = c.company_name || c.contact_name || c.email || `Customer #${c.id}`;
                const detail = c.company_name && c.contact_name ? ` (${c.contact_name})` : (c.email && c.email !== label ? ` (${c.email})` : "");
                return (
                  <option key={c.id} value={c.id}>
                    {label}{detail}
                  </option>
                );
              })}
            </select>
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">
              Plan *
            </label>
            <select
              className={selectClass}
              value={form.plan_id}
              onChange={(e) => handlePlanChange(e.target.value)}
              required
            >
              <option value="">Select plan…</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {p.currency || "USD"} {parseFloat(p.base_price).toFixed(2)} / {p.billing_interval}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Selected Plan Details Card */}
        {selectedPlan && (
          <div className="p-3.5 rounded-xl bg-slate-900/80 border border-brand-500/30 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div>
              <span className="text-slate-400">Selected Plan: </span>
              <span className="font-semibold text-white">{selectedPlan.name}</span>
              <span className="ml-2 font-mono text-[11px] text-brand-400">({selectedPlan.code})</span>
            </div>
            <div className="flex items-center gap-4 text-slate-300">
              <div>
                <span className="text-slate-400">Interval: </span>
                <span className="capitalize font-medium text-white">{selectedPlan.billing_interval}</span>
              </div>
              <div>
                <span className="text-slate-400">Base Price: </span>
                <span className="font-semibold text-emerald-400">
                  {selectedPlan.currency || "USD"} {parseFloat(selectedPlan.base_price || 0).toFixed(2)}
                </span>
              </div>
              {selectedPlan.trial_days > 0 && (
                <div>
                  <span className="text-slate-400">Trial: </span>
                  <span className="font-medium text-amber-300">{selectedPlan.trial_days} days</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Start Date + Auto-Renew */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input
            label="Start Date *"
            type="date"
            icon={Calendar}
            value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            required
          />
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={form.auto_renew}
                onChange={(e) => setForm({ ...form, auto_renew: e.target.checked })}
                className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-brand-500"
              />
              <span className="text-sm text-slate-300">Auto-renew subscription</span>
            </label>
          </div>
        </div>

        {/* Line Items */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Line Items *
            </span>
            <button
              type="button"
              onClick={addLine}
              className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-medium transition"
            >
              <Plus className="w-3.5 h-3.5" /> Add Line
            </button>
          </div>

          <div className="rounded-xl border border-slate-800 overflow-hidden">
            <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-slate-800/60 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              <div className="col-span-4">Product</div>
              <div className="col-span-3">Description</div>
              <div className="col-span-1 text-right">Qty</div>
              <div className="col-span-2 text-right">Unit Price</div>
              <div className="col-span-1 text-right">Disc%</div>
              <div className="col-span-1" />
            </div>

            {lines.map((line, idx) => (
              <div
                key={idx}
                className="grid grid-cols-12 gap-2 px-3 py-2 border-t border-slate-800 items-center"
              >
                <div className="col-span-4">
                  <select
                    className={`${selectClass} text-xs py-1.5`}
                    value={line.product_id}
                    onChange={(e) => handleLineProductChange(idx, e.target.value)}
                    required
                  >
                    <option value="">Select product…</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name} ({p.currency || "USD"} {parseFloat(p.default_price || 0).toFixed(2)})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-span-3">
                  <input
                    className={`${selectClass} text-xs py-1.5`}
                    placeholder="Description"
                    value={line.description}
                    onChange={(e) => updateLine(idx, "description", e.target.value)}
                  />
                </div>
                <div className="col-span-1">
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.quantity}
                    onChange={(e) => updateLine(idx, "quantity", e.target.value)}
                    required
                  />
                </div>
                <div className="col-span-2">
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.unit_price}
                    onChange={(e) => updateLine(idx, "unit_price", e.target.value)}
                    required
                  />
                </div>
                <div className="col-span-1">
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.01"
                    className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.discount_percent}
                    onChange={(e) => updateLine(idx, "discount_percent", e.target.value)}
                  />
                </div>
                <div className="col-span-1 flex justify-end">
                  {lines.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeLine(idx)}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 transition"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {/* Totals Row */}
            <div className="flex justify-end items-center gap-3 px-3 py-2.5 bg-slate-800/40 border-t border-slate-700">
              <span className="text-xs text-slate-400">Recurring Total:</span>
              <span className="text-sm font-bold text-white">
                {selectedPlan?.currency || "USD"} {recurringTotal.toFixed(2)}
              </span>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" size="sm" isLoading={isLoading}>
            Create Subscription
          </Button>
        </div>
      </form>
    </Modal>
  );
}

export default CreateSubscriptionModal;
