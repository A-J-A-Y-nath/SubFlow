import React, { useState, useEffect } from "react";
import { Menu, LogOut, CheckCircle, AlertCircle, Sparkles } from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import dashboardService from "../../services/dashboardService";
import Button from "../ui/Button";

export function Navbar({ onOpenMobile, currentTitle = "Dashboard" }) {
  const { user, logout } = useAuth();
  const [backendHealth, setBackendHealth] = useState({ status: "checking" });

  useEffect(() => {
    let isMounted = true;
    async function checkHealth() {
      try {
        const res = await dashboardService.getHealth();
        if (isMounted) {
          setBackendHealth({ status: res.success ? "connected" : "degraded" });
        }
      } catch {
        if (isMounted) {
          setBackendHealth({ status: "offline" });
        }
      }
    }

    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <header className="sticky top-0 z-30 flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 sm:px-6 backdrop-blur-md">
      <div className="flex items-center gap-3">
        <button
          onClick={onOpenMobile}
          className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <h1 className="text-base font-bold text-white tracking-tight">{currentTitle}</h1>
          <span className="text-slate-600 hidden sm:inline">/</span>
          <span className="text-xs text-slate-400 hidden sm:inline">Workspace</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Backend Connectivity Status Pill */}
        <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono border bg-slate-900 border-slate-800 text-slate-300">
          <span
            className={`w-2 h-2 rounded-full ${
              backendHealth.status === "connected"
                ? "bg-emerald-400 animate-pulse"
                : backendHealth.status === "degraded"
                ? "bg-amber-400"
                : "bg-rose-400"
            }`}
          />
          <span className="text-[11px]">
            {backendHealth.status === "connected"
              ? "Flask + Neon Live"
              : backendHealth.status === "degraded"
              ? "Degraded"
              : "Checking API..."}
          </span>
        </div>

        {/* User Info & Logout Button */}
        <div className="flex items-center gap-2 pl-2 border-l border-slate-800">
          <div className="text-right hidden md:block">
            <p className="text-xs font-medium text-slate-200">{user?.full_name || user?.email}</p>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider">{user?.role}</p>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Sign Out</span>
          </Button>
        </div>
      </div>
    </header>
  );
}

export default Navbar;
