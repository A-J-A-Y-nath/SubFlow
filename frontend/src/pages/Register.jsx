import React, { useState } from "react";
import { User, Mail, Lock, Building, Check, X, ArrowRight, ShieldCheck, Zap, Eye, EyeOff } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import Alert from "../components/common/Alert";

export function Register({ onNavigate }) {
  const { register } = useAuth();
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    company_name: "",
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Live Password Checklist
  const password = formData.password;
  const checks = [
    { label: "More than 8 characters", valid: password.length > 8 },
    { label: "At least one uppercase letter (A-Z)", valid: /[A-Z]/.test(password) },
    { label: "At least one lowercase letter (a-z)", valid: /[a-z]/.test(password) },
    { label: "At least one special character (!@#$%...)", valid: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password) },
  ];
  const isPasswordValid = checks.every((c) => c.valid);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!isPasswordValid) {
      setError("Please ensure your password meets all complexity requirements.");
      return;
    }

    setIsLoading(true);
    try {
      await register(formData);
      onNavigate("/dashboard");
    } catch (err) {
      setError(err.message || "Registration failed. Please check your information.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center p-4 bg-slate-950 selection:bg-brand-500 selection:text-white">
      {/* Background glow effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-96 h-96 bg-brand-600/15 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md space-y-6 z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-500 text-white shadow-xl shadow-brand-500/25 mb-2">
            <Zap className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Create SubFlow Account
          </h1>
          <p className="text-xs text-slate-400">
            Set up your organization for subscription lifecycle automation
          </p>
        </div>

        {/* Form Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-5">
          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          {/* Role Policy Notice */}
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-brand-500/10 border border-brand-500/20 text-xs text-brand-300">
            <ShieldCheck className="w-4 h-4 shrink-0 mt-0.5 text-brand-400" />
            <div>
              <span className="font-semibold text-white">RBAC Architecture:</span> The first account created bootstraps as <span className="underline font-medium">Admin</span>. Subsequent registrations become <span className="underline font-medium">Customer</span> accounts. Staff accounts can only be created by an Admin.
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="First Name"
                placeholder="Jane"
                icon={User}
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                required
              />
              <Input
                label="Last Name"
                placeholder="Doe"
                icon={User}
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                required
              />
            </div>

            <Input
              label="Company / Organization"
              placeholder="Acme Innovations Inc"
              icon={Building}
              value={formData.company_name}
              onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
              required
            />

            <Input
              label="Work Email"
              type="email"
              placeholder="jane@company.com"
              icon={Mail}
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />

            <div className="space-y-2">
              <Input
                label="Password"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••••••"
                icon={Lock}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                rightElement={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="text-slate-400 hover:text-slate-200 transition focus:outline-none p-1 rounded"
                    title={showPassword ? "Hide password" : "Show password"}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                    ) : (
                      <Eye className="w-4 h-4 text-slate-400 hover:text-slate-200" />
                    )}
                  </button>
                }
              />

              {/* Password checklist */}
              {formData.password.length > 0 && (
                <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 space-y-1">
                  <p className="text-[11px] font-semibold text-slate-400">Security Requirements:</p>
                  {checks.map((c, i) => (
                    <div key={i} className="flex items-center gap-1.5 text-[11px]">
                      {c.valid ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : (
                        <X className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      )}
                      <span className={c.valid ? "text-emerald-400" : "text-slate-400"}>
                        {c.label}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full font-semibold"
              isLoading={isLoading}
              disabled={!isPasswordValid}
            >
              Complete Registration
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </form>
        </div>

        {/* Footer sign in link */}
        <div className="text-center text-xs text-slate-400">
          Already have an account?{" "}
          <button
            onClick={() => onNavigate("/login")}
            className="font-medium text-brand-400 hover:text-brand-300 underline underline-offset-4"
          >
            Sign in here
          </button>
        </div>
      </div>
    </div>
  );
}

export default Register;
