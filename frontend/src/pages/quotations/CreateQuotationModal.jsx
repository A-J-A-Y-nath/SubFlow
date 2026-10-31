import React, { useState, useEffect } from "react";
import { Plus, Trash2, Calendar } from "lucide-react";
import Modal from "../../components/ui/Modal";
import Input from "../../components/ui/Input";
import Button from "../../components/ui/Button";
import Alert from "../../components/common/Alert";
import subflowService from "../../services/subflowService";

const TAX_RATE = 0.18; // Must match backend quotation_service.TAX_RATE
const emptyLine = () => ({ product_id: "", description: "", quantity: 1, unit_price: "", discount_percent: 0 });

export function CreateQuotationModal({ isOpen, onClose, onSuccess }) {
  const [customers, setCustomers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [products, setProducts] = useState([]);
  const [form, setForm] = useState({
    customer_id: "",
    plan_id: "",
    issue_date: new Date().toISOString().slice(0, 10),
    valid_until: "",
    notes: "",
    terms_and_conditions: "",
  });
  const [lines, setLines] = useState([emptyLine()]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!isOpen) return;
    Promise.all([
      subflowService.getCustomers({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
      subflowService.getPlans({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
      subflowService.getProducts({ per_page: 100 }).catch(() => ({ data: { items: [] } })),
    ]).then(([c, p, pr]) => {
      setCustomers(Array.isArray(c?.data) ? c.data : c?.data?.items || []);
      setPlans(Array.isArray(p?.data) ? p.data : p?.data?.items || []);
      setProducts(Array.isArray(pr?.data) ? pr.data : pr?.data?.items || []);
    });
  }, [isOpen]);

  const handlePlanChange = (selectedPlanId) => {
    setForm((prev) => ({ ...prev, plan_id: selectedPlanId }));
    const plan = plans.find((p) => String(p.id) === String(selectedPlanId));
    if (plan) {
      const planPrice = parseFloat(plan.base_price) || 0;
      const planDesc = `${plan.name} (${plan.billing_interval || "monthly"})`;
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

  const handleLineProductChange = (idx, productId) => {
    const prod = products.find((p) => String(p.id) === String(productId));
    setLines((prev) =>
      prev.map((l, i) =>
        i === idx
          ? { ...l, product_id: productId, description: prod?.name || l.description, unit_price: prod?.default_price ?? l.unit_price }
          : l
      )
    );
  };

  const updateLine = (idx, field, value) =>
    setLines((prev) => prev.map((l, i) => (i === idx ? { ...l, [field]: value } : l)));

  const addLine = () => setLines((prev) => [...prev, emptyLine()]);
  const removeLine = (idx) => setLines((prev) => prev.filter((_, i) => i !== idx));

  // Live totals
  const totals = lines.reduce(
    (acc, l) => {
      const qty = parseFloat(l.quantity) || 0;
      const price = parseFloat(l.unit_price) || 0;
      const disc = parseFloat(l.discount_percent) || 0;
      const gross = qty * price;
      const discAmt = gross * (disc / 100);
      acc.subtotal += gross;
      acc.discount += discAmt;
      return acc;
    },
    { subtotal: 0, discount: 0 }
  );
  const taxable = totals.subtotal - totals.discount;
  const tax = taxable * TAX_RATE;
  const total = taxable + tax;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!form.valid_until) { setError("Valid Until date is required."); return; }
    setIsLoading(true);
    try {
      const res = await subflowService.createQuotation({
        ...form,
        customer_id: parseInt(form.customer_id),
        plan_id: form.plan_id ? parseInt(form.plan_id) : null,
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
      setForm({ customer_id: "", plan_id: "", issue_date: new Date().toISOString().slice(0, 10), valid_until: "", notes: "", terms_and_conditions: "" });
    } catch (err) {
      setError(err.message || "Failed to create quotation.");
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
      title="New Quotation"
      description="Draft a pricing proposal for a customer. Confirm it later to generate a subscription."
      maxWidth="max-w-3xl"
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

        {/* Customer + Plan */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">Customer *</label>
            <select className={selectClass} value={form.customer_id} onChange={(e) => setForm({ ...form, customer_id: e.target.value })} required>
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
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">Plan (optional)</label>
            <select className={selectClass} value={form.plan_id} onChange={(e) => handlePlanChange(e.target.value)}>
              <option value="">No plan…</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} — {p.currency || "USD"} {parseFloat(p.base_price).toFixed(2)} / {p.billing_interval}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Dates */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Input label="Issue Date *" type="date" icon={Calendar} value={form.issue_date}
            onChange={(e) => setForm({ ...form, issue_date: e.target.value })} required />
          <Input label="Valid Until *" type="date" icon={Calendar} value={form.valid_until}
            onChange={(e) => setForm({ ...form, valid_until: e.target.value })} required />
        </div>

        {/* Line Items */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Line Items *</span>
            <button type="button" onClick={addLine}
              className="flex items-center gap-1.5 text-xs text-brand-400 hover:text-brand-300 font-medium transition">
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
              <div key={idx} className="grid grid-cols-12 gap-2 px-3 py-2 border-t border-slate-800 items-center">
                <div className="col-span-4">
                  <select className={`${selectClass} text-xs py-1.5`} value={line.product_id}
                    onChange={(e) => handleLineProductChange(idx, e.target.value)} required>
                    <option value="">Select…</option>
                    {products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div className="col-span-3">
                  <input className={`${selectClass} text-xs py-1.5`} placeholder="Description"
                    value={line.description} onChange={(e) => updateLine(idx, "description", e.target.value)} />
                </div>
                <div className="col-span-1">
                  <input type="number" min="0.01" step="0.01" className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.quantity} onChange={(e) => updateLine(idx, "quantity", e.target.value)} required />
                </div>
                <div className="col-span-2">
                  <input type="number" min="0" step="0.01" className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.unit_price} onChange={(e) => updateLine(idx, "unit_price", e.target.value)} required />
                </div>
                <div className="col-span-1">
                  <input type="number" min="0" max="100" step="0.01" className={`${selectClass} text-xs py-1.5 text-right`}
                    value={line.discount_percent} onChange={(e) => updateLine(idx, "discount_percent", e.target.value)} />
                </div>
                <div className="col-span-1 flex justify-end">
                  {lines.length > 1 && (
                    <button type="button" onClick={() => removeLine(idx)}
                      className="p-1 rounded text-slate-500 hover:text-rose-400 transition">
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            ))}

            {/* Live Totals */}
            <div className="px-3 py-3 bg-slate-800/40 border-t border-slate-700 grid grid-cols-2 gap-2 text-xs">
              {[
                ["Subtotal", `₹${totals.subtotal.toFixed(2)}`],
                ["Discount", `−₹${totals.discount.toFixed(2)}`],
                ["18% GST", `₹${tax.toFixed(2)}`],
                ["Total", `₹${total.toFixed(2)}`],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between items-center col-span-1">
                  <span className={`text-slate-400 ${label === "Total" ? "font-semibold text-white" : ""}`}>{label}:</span>
                  <span className={`font-semibold ${label === "Total" ? "text-white text-sm" : "text-slate-200"}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Notes */}
        <div className="space-y-1.5">
          <label className="block text-xs font-semibold uppercase tracking-wider text-slate-300">Notes</label>
          <textarea
            className={`${selectClass} h-16 resize-none text-xs`}
            placeholder="Internal notes or additional context…"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button type="button" variant="outline" size="sm" onClick={onClose} disabled={isLoading}>Cancel</Button>
          <Button type="submit" variant="primary" size="sm" isLoading={isLoading}>Create Quotation</Button>
        </div>
      </form>
    </Modal>
  );
}

export default CreateQuotationModal;
