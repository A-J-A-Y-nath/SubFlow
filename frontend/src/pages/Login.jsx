import React, { useState } from "react";
import { Lock, Mail, Zap, Shield, ArrowRight, UserCheck } from "lucide-react";
import { useAuth } from "../hooks/useAuth";
import Input from "../components/ui/Input";
import Button from "../components/ui/Button";
import Alert from "../components/common/Alert";

export function Login({ onNavigate }) {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    try {
      await login(email, password);
      onNavigate("/dashboard");
    } catch (err) {
      setError(err.message || "Invalid email or password. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  // Demo credential quick-fill helpers for hackathon testing
  const setDemoCredentials = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
  };

  return (
    <div className="flex min-h-screen w-full items-center justify-center p-4 bg-slate-950 selection:bg-brand-500 selection:text-white">
      {/* Background glow effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-brand-600/15 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl"></div>
      </div>

      <div className="relative w-full max-w-md space-y-6 z-10">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-tr from-brand-600 to-indigo-500 text-white shadow-xl shadow-brand-500/25 mb-2">
            <Zap className="h-6 w-6" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">
            Welcome to SubFlow
          </h1>
          <p className="text-xs text-slate-400">
            Subscription Management & Recurring Invoicing Engine
          </p>
        </div>

        {/* Login Card */}
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6 sm:p-8 shadow-2xl backdrop-blur-xl space-y-5">
          {error && <Alert type="error" message={error} onClose={() => setError(null)} />}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Work Email"
              type="email"
              placeholder="you@company.com"
              icon={Mail}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••••••"
              icon={Lock}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full font-semibold"
              isLoading={isLoading}
            >
              Sign In to Dashboard
              <ArrowRight className="w-4 h-4 ml-1.5" />
            </Button>
          </form>

          {/* Quick-Fill Demo Pills */}
          <div className="pt-3 border-t border-slate-800/80">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500 mb-2 text-center">
              Quick Test Accounts (Make-A-Ton 9.0)
            </p>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setDemoCredentials("admin@subflow.io", "SubFlow#Admin2026!")}
                className="px-2 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-brand-500/50 text-[11px] text-slate-300 transition text-center"
              >
                <div className="font-semibold text-brand-400">Admin</div>
                <div className="text-[10px] text-slate-500 truncate">admin@subflow</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoCredentials("staff@subflow.io", "SubFlow#Staff2026!")}
                className="px-2 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-amber-500/50 text-[11px] text-slate-300 transition text-center"
              >
                <div className="font-semibold text-amber-400">Staff</div>
                <div className="text-[10px] text-slate-500 truncate">staff@subflow</div>
              </button>
              <button
                type="button"
                onClick={() => setDemoCredentials("customer@subflow.io", "SubFlow#Customer2026!")}
                className="px-2 py-1.5 rounded-lg border border-slate-800 bg-slate-950/60 hover:bg-slate-800 hover:border-emerald-500/50 text-[11px] text-slate-300 transition text-center"
              >
                <div className="font-semibold text-emerald-400">Customer</div>
                <div className="text-[10px] text-slate-500 truncate">customer@subflow</div>
              </button>
            </div>
          </div>
        </div>

        {/* Footer registration link */}
        <div className="text-center text-xs text-slate-400">
          Need a new account?{" "}
          <button
            onClick={() => onNavigate("/register")}
            className="font-medium text-brand-400 hover:text-brand-300 underline underline-offset-4"
          >
            Register your company
          </button>
        </div>
      </div>
    </div>
  );
}

export default Login;
