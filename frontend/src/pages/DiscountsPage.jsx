import React, { useState, useEffect } from "react";
import {
  Percent,
  Plus,
  Tag,
  Check,
  Copy,
  CheckCircle2,
  XCircle,
  Search,
  RefreshCw,
  Power,
  Calendar,
  Layers,
  Edit2
} from "lucide-react";
import subflowService from "../services/subflowService";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Modal from "../components/ui/Modal";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { formatDate, formatCurrency } from "../lib/utils";
import { useAuth } from "../hooks/useAuth";

export function DiscountsPage() {
  const { user } = useAuth();
  const isStaffOrAdmin = user?.role === "admin" || user?.role === "staff";

  // Data state
  const [discounts, setDiscounts] = useState([]);
  const [plans, setPlans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("all");
  const [copiedCode, setCopiedCode] = useState(null);

  // Live Coupon Validator Tool
  const [testCode, setTestCode] = useState("");
  const [testAmount, setTestAmount] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [testError, setTestError] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  // Create / Edit Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingDiscountId, setEditingDiscountId] = useState(null);
  const [form, setForm] = useState({
    code: "",
    name: "",
    description: "",
    discount_type: "percentage",
    value: "",
    min_order_amount: "0.00",
    max_discount_amount: "",
    valid_from: "",
    valid_to: "",
    max_uses: "",
    is_active: true,
    applicable_plans: []
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Load discounts and plans
  const fetchDiscounts = async () => {
    try {
      setError(null);
      const params = {};
      if (activeFilter !== "all") params.is_active = activeFilter === "active";
      if (searchQuery.trim()) params.search = searchQuery.trim();

      const [discRes, planRes] = await Promise.all([
        subflowService.getDiscounts(params),
        subflowService.getPlans().catch(() => ({ data: { items: [] } }))
      ]);

      if (discRes.success) {
        setDiscounts(discRes.data?.items || []);
      }
      setPlans(planRes.data?.items || []);
    } catch (err) {
      setError(err.message || "Failed to load discount rules.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDiscounts();
  }, [activeFilter]);

  // Live validate tester
  const handleTestCoupon = async (e) => {
    e.preventDefault();
    if (!testCode.trim()) return;

    setTestError(null);
    setTestResult(null);
    setIsValidating(true);
    try {
      const params = {};
      if (testAmount) params.amount = parseFloat(testAmount);
      const res = await subflowService.validateCoupon(testCode.trim(), params);
      if (res.success) {
        setTestResult(res.data);
      }
    } catch (err) {
      setTestError(err.message || "Coupon code is invalid or does not meet minimum order constraints.");
    } finally {
      setIsValidating(false);
    }
  };

  // Toggle active/inactive
  const handleToggleStatus = async (id) => {
    try {
      const res = await subflowService.toggleDiscountStatus(id);
      if (res.success) {
        setSuccessMsg(`Coupon '${res.data?.code}' updated.`);
        fetchDiscounts();
      }
    } catch (err) {
      setError(err.message || "Failed to update discount status.");
    }
  };

  // Open modal for Create
  const handleOpenCreate = () => {
    setEditingDiscountId(null);
    setForm({
      code: "",
      name: "",
      description: "",
      discount_type: "percentage",
      value: "20.00",
      min_order_amount: "0.00",
      max_discount_amount: "",
      valid_from: "",
      valid_to: "",
      max_uses: "",
      is_active: true,
      applicable_plans: []
    });
    setIsCreateOpen(true);
  };

  // Open modal for Edit
  const handleOpenEdit = (rule) => {
    setEditingDiscountId(rule.id);
    setForm({
      code: rule.code,
      name: rule.name,
      description: rule.description || "",
      discount_type: rule.discount_type,
      value: String(rule.value),
      min_order_amount: String(rule.min_order_amount || "0.00"),
      max_discount_amount: rule.max_discount_amount ? String(rule.max_discount_amount) : "",
      valid_from: rule.valid_from ? rule.valid_from.split("T")[0] : "",
      valid_to: rule.valid_to ? rule.valid_to.split("T")[0] : "",
      max_uses: rule.max_uses ? String(rule.max_uses) : "",
      is_active: rule.is_active,
      applicable_plans: rule.applicable_plans || []
    });
    setIsCreateOpen(true);
  };

  // Submit create or edit
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.code || !form.name || !form.value) {
      setError("Code, Name, and Value are required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const payload = {
        code: form.code.trim().toUpperCase(),
        name: form.name.trim(),
        description: form.description || null,
        discount_type: form.discount_type,
        value: parseFloat(form.value),
        min_order_amount: parseFloat(form.min_order_amount || 0),
        max_discount_amount: form.max_discount_amount ? parseFloat(form.max_discount_amount) : null,
        valid_from: form.valid_from || null,
        valid_to: form.valid_to || null,
        max_uses: form.max_uses ? parseInt(form.max_uses) : null,
        is_active: form.is_active,
        applicable_plans: form.applicable_plans
      };

      let res;
      if (editingDiscountId) {
        res = await subflowService.updateDiscount(editingDiscountId, payload);
      } else {
        res = await subflowService.createDiscount(payload);
      }

      if (res.success) {
        setSuccessMsg(`Discount rule '${res.data?.code}' saved successfully!`);
        setIsCreateOpen(false);
        fetchDiscounts();
      }
    } catch (err) {
      setError(err.message || "Failed to save discount rule.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const copyToClipboard = (code) => {
    navigator.clipboard?.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // Aggregate stats
  const stats = React.useMemo(() => {
    let activeCount = 0;
    let totalUses = 0;
    discounts.forEach((d) => {
      if (d.is_active && d.is_valid) activeCount++;
      totalUses += d.current_uses || 0;
    });
    return { total: discounts.length, activeCount, totalUses };
  }, [discounts]);

  return (
    <div className="space-y-6">
      {/* Top Stat Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Active Campaigns</span>
          <p className="text-xl font-bold text-emerald-400 mt-1">{stats.activeCount}</p>
          <span className="text-[10px] text-slate-500">Out of {stats.total} configured promo rules</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Coupon Redemptions</span>
          <p className="text-xl font-bold text-brand-400 mt-1">{stats.totalUses}</p>
          <span className="text-[10px] text-slate-500">Applied across checkout & invoices</span>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 col-span-2 lg:col-span-1">
          <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Discount Engine</span>
          <p className="text-xl font-bold text-white mt-1">Operational</p>
          <span className="text-[10px] text-slate-500">Atomic usage & concurrency safe</span>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Discounts & Promotion Rules</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure coupons, campaign rules, percentage discounts, and usage limits
          </p>
        </div>

        {isStaffOrAdmin && (
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            <Plus className="w-4 h-4 mr-1.5" />
            Create Discount Rule
          </Button>
        )}
      </div>

      {/* Notifications */}
      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}
      {successMsg && <Alert type="success" message={successMsg} onClose={() => setSuccessMsg(null)} />}

      {/* Live Coupon Validation Tester Tool */}
      <Card className="border-brand-500/20 bg-slate-900/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-white">
            <Tag className="w-4 h-4 text-brand-400" />
            Live Coupon Validation Engine
          </CardTitle>
          <CardDescription>
            Simulate promo code qualification against backend eligibility, thresholds, and limits
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTestCoupon} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="max-w-xs w-full">
              <Input
                placeholder="Enter promo code (e.g. SAVE20)..."
                value={testCode}
                onChange={(e) => setTestCode(e.target.value.toUpperCase())}
                required
              />
            </div>
            <div className="w-36">
              <Input
                type="number"
                placeholder="Order Amount ($)"
                min="0"
                step="0.01"
                value={testAmount}
                onChange={(e) => setTestAmount(e.target.value)}
              />
            </div>
            <Button type="submit" variant="secondary" size="md" disabled={isValidating}>
              {isValidating ? "Validating..." : "Validate Code"}
            </Button>
          </form>

          {testResult && (
            <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  <strong>{testResult.code}</strong> is valid:{" "}
                  {testResult.discount_type === "percentage" ? `${testResult.value}% OFF` : `$${testResult.value} OFF`}
                  {testResult.calculated_discount > 0 && ` (Saving: $${testResult.calculated_discount.toFixed(2)})`}
                </span>
              </div>
              <Badge variant="success">Active</Badge>
            </div>
          )}

          {testError && (
            <div className="mt-3">
              <Alert type="error" message={testError} onClose={() => setTestError(null)} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 p-3 rounded-xl bg-slate-900/80 border border-slate-800">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search code or campaign name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && fetchDiscounts()}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <div className="flex items-center gap-2">
          {["all", "active", "inactive"].map((st) => (
            <button
              key={st}
              onClick={() => setActiveFilter(st)}
              className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all ${
                activeFilter === st
                  ? "bg-brand-600 text-white shadow"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              {st}
            </button>
          ))}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setIsRefreshing(true);
              fetchDiscounts();
            }}
            className="p-1.5 ml-1"
            title="Refresh List"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${isRefreshing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Rules Grid */}
      {isLoading ? (
        <LoadingSpinner message="Loading promotion rules..." />
      ) : discounts.length === 0 ? (
        <EmptyState
          title="No Discount Rules Configured"
          description="Create promotional discount rules or seasonal coupons to apply during quotation or checkout."
          icon={Percent}
          actionText={isStaffOrAdmin ? "Create First Rule" : undefined}
          onAction={isStaffOrAdmin ? handleOpenCreate : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {discounts.map((rule) => {
            const isExhausted = rule.max_uses !== null && rule.current_uses >= rule.max_uses;
            const isLive = rule.is_active && rule.is_valid && !isExhausted;

            return (
              <div
                key={rule.id}
                className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 hover:border-slate-700 transition relative flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h4 className="text-base font-bold text-white">{rule.name}</h4>
                      <p className="text-xs text-slate-400 mt-0.5 line-clamp-2">
                        {rule.description || "Promotional discount rule"}
                      </p>
                    </div>
                    <Badge variant={isLive ? "success" : "danger"}>
                      {!rule.is_active ? "Inactive" : isExhausted ? "Exhausted" : isLive ? "Active" : "Expired"}
                    </Badge>
                  </div>

                  {/* Coupon Code Pill */}
                  <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs">
                    <span className="font-bold text-brand-400 tracking-wider">{rule.code}</span>
                    <button
                      onClick={() => copyToClipboard(rule.code)}
                      className="text-slate-400 hover:text-white p-1 rounded transition"
                      title="Copy code"
                    >
                      {copiedCode === rule.code ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                      ) : (
                        <Copy className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>

                  {/* Benefit & Thresholds */}
                  <div className="space-y-1.5 text-xs text-slate-400 pt-1 border-t border-slate-800/60">
                    <div className="flex justify-between">
                      <span>Benefit:</span>
                      <span className="font-semibold text-white">
                        {rule.discount_type === "percentage" ? `${rule.value}% OFF` : `$${rule.value} Fixed Discount`}
                      </span>
                    </div>
                    {rule.min_order_amount > 0 && (
                      <div className="flex justify-between">
                        <span>Min Order:</span>
                        <span className="text-slate-300">${rule.min_order_amount}</span>
                      </div>
                    )}
                    {rule.max_discount_amount && (
                      <div className="flex justify-between">
                        <span>Max Cap:</span>
                        <span className="text-slate-300">${rule.max_discount_amount}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span>Usage:</span>
                      <span className="text-slate-300">
                        {rule.current_uses} {rule.max_uses ? `/ ${rule.max_uses} used` : "redemptions"}
                      </span>
                    </div>
                    {rule.valid_to && (
                      <div className="flex justify-between">
                        <span>Expires:</span>
                        <span className="text-slate-300">{formatDate(rule.valid_to)}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Staff / Admin Actions */}
                {isStaffOrAdmin && (
                  <div className="flex items-center justify-between pt-3 border-t border-slate-800/80">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggleStatus(rule.id)}
                      className={`text-xs py-1 px-2.5 h-auto ${
                        rule.is_active ? "text-amber-400 hover:text-amber-300" : "text-emerald-400 hover:text-emerald-300"
                      }`}
                    >
                      <Power className="w-3 h-3 mr-1" />
                      {rule.is_active ? "Deactivate" : "Activate"}
                    </Button>

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenEdit(rule)}
                      className="text-xs py-1 px-2.5 h-auto text-slate-300 hover:text-white"
                    >
                      <Edit2 className="w-3 h-3 mr-1" />
                      Edit
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Create / Edit Modal */}
      {isCreateOpen && (
        <Modal
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          title={editingDiscountId ? "Edit Discount Rule" : "Create Promotional Rule"}
          size="md"
        >
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Coupon Code <span className="text-rose-400">*</span>
                </label>
                <Input
                  placeholder="e.g. SUMMER25"
                  value={form.code}
                  onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })}
                  disabled={Boolean(editingDiscountId)}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Discount Type <span className="text-rose-400">*</span>
                </label>
                <select
                  value={form.discount_type}
                  onChange={(e) => setForm({ ...form, discount_type: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-brand-500"
                >
                  <option value="percentage">Percentage (%)</option>
                  <option value="fixed">Fixed Amount ($)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Campaign Name <span className="text-rose-400">*</span>
              </label>
              <Input
                placeholder="e.g. Summer Kickoff 2026 Promo"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Value <span className="text-rose-400">*</span>
                </label>
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder={form.discount_type === "percentage" ? "20" : "50"}
                  value={form.value}
                  onChange={(e) => setForm({ ...form, value: e.target.value })}
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Min Order ($)</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  value={form.min_order_amount}
                  onChange={(e) => setForm({ ...form, min_order_amount: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Max Cap ($)</label>
                <Input
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="Optional"
                  value={form.max_discount_amount}
                  onChange={(e) => setForm({ ...form, max_discount_amount: e.target.value })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Valid From</label>
                <Input
                  type="date"
                  value={form.valid_from}
                  onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Valid Until</label>
                <Input
                  type="date"
                  value={form.valid_to}
                  onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Maximum Uses</label>
              <Input
                type="number"
                min="1"
                placeholder="Leave blank for unlimited redemptions"
                value={form.max_uses}
                onChange={(e) => setForm({ ...form, max_uses: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Description</label>
              <textarea
                rows={2}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Optional customer-facing or internal promo notes..."
                className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
              <Button type="button" variant="ghost" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? "Saving..." : editingDiscountId ? "Update Rule" : "Create Rule"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}

export default DiscountsPage;
