import React, { useState, useEffect } from "react";
import { Percent, Plus, Tag, Check, Copy, CheckCircle2 } from "lucide-react";
import subflowService from "../services/subflowService";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import EmptyState from "../components/common/EmptyState";
import LoadingSpinner from "../components/common/LoadingSpinner";
import Alert from "../components/common/Alert";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "../components/ui/Card";
import { formatDate } from "../lib/utils";

export function DiscountsPage() {
  const [discounts, setDiscounts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [testCode, setTestCode] = useState("");
  const [testResult, setTestResult] = useState(null);
  const [testError, setTestError] = useState(null);
  const [copiedCode, setCopiedCode] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function fetchDiscounts() {
      try {
        const res = await subflowService.getDiscounts();
        if (isMounted && res.success) {
          setDiscounts(res.data?.items || []);
        }
      } catch (err) {
        if (isMounted) setError(err.message || "Failed to load discount rules.");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    }

    fetchDiscounts();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleTestCoupon = async (e) => {
    e.preventDefault();
    if (!testCode.trim()) return;

    setTestError(null);
    setTestResult(null);
    try {
      const res = await subflowService.validateCoupon(testCode.trim());
      if (res.success) {
        setTestResult(res.data);
      }
    } catch (err) {
      setTestError(err.message || "Coupon code is invalid or expired.");
    }
  };

  const copyToClipboard = (code) => {
    navigator.clipboard?.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white">Discounts & Promotion Rules</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Configure coupons, campaign rules, percentage discounts, and usage limits
          </p>
        </div>

        <Button variant="primary" size="sm" onClick={() => alert("Discounts Developer will connect create coupon rule dialog here!")}>
          <Plus className="w-4 h-4 mr-1.5" />
          Create Discount Rule
        </Button>
      </div>

      {/* Developer note */}
      <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-center justify-between">
        <span className="font-mono text-slate-300">
          <strong className="text-brand-400 font-semibold">Teammate Module:</strong> Discounts API endpoint: <code className="text-slate-200">GET /api/v1/discounts</code>
        </span>
        <Badge variant="brand" className="text-[10px]">Ready to Extend</Badge>
      </div>

      {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

      {/* Coupon Live Validation Tool */}
      <Card className="border-brand-500/20 bg-slate-900/60">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2 text-white">
            <Tag className="w-4 h-4 text-brand-400" />
            Live Coupon Validation Tester
          </CardTitle>
          <CardDescription>
            Test any promo code against the backend validation engine rules
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleTestCoupon} className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="max-w-xs w-full">
              <Input
                placeholder="Enter coupon code (e.g. SAVE20)..."
                value={testCode}
                onChange={(e) => setTestCode(e.target.value.toUpperCase())}
              />
            </div>
            <Button type="submit" variant="secondary" size="md">
              Validate Code
            </Button>
          </form>

          {testResult && (
            <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  <strong>{testResult.code}</strong> is valid:{" "}
                  {testResult.discount_type === "percentage" ? `${testResult.value}% OFF` : `$${testResult.value} OFF`}
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

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner message="Loading promotion rules..." />
      ) : discounts.length === 0 ? (
        <EmptyState
          title="No Discount Rules Configured"
          description="Create promotional discount rules or seasonal coupons to apply during quotation or checkout."
          developerNote="Model: backend/models/discount.py | Controller: backend/routes/discounts.py"
          icon={Percent}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {discounts.map((rule) => (
            <div
              key={rule.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 hover:border-slate-700 transition"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-base font-bold text-white">{rule.name}</h4>
                  <p className="text-xs text-slate-400 mt-1">{rule.description || "Promotional campaign"}</p>
                </div>
                <Badge variant={rule.is_valid ? "success" : "danger"}>
                  {rule.is_valid ? "Valid" : "Expired"}
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

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <span>Benefit:</span>
                <span className="font-semibold text-white">
                  {rule.discount_type === "percentage" ? `${rule.value}% OFF` : `$${rule.value} Fixed`}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default DiscountsPage;
