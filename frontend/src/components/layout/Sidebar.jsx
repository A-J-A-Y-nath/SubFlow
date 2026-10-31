import React from "react";
import {
  LayoutDashboard,
  Package,
  Layers,
  Repeat,
  FileText,
  Receipt,
  CreditCard,
  Percent,
  BarChart3,
  UserPlus,
  Shield,
  Zap,
} from "lucide-react";
import { useAuth } from "../../hooks/useAuth";
import { Badge } from "../ui/Badge";
import { cn } from "../../lib/utils";
export function Sidebar({ currentPath, onNavigate, isMobileOpen, onCloseMobile, onOpenCreateStaff }) {
  const { user, role, isAdmin, isCustomer } = useAuth();

  const navItems = [
    { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard, roles: ["admin", "staff", "customer"] },
    { label: "Plans", path: "/plans", icon: Layers, roles: ["admin", "staff", "customer"] },
    { label: "Subscriptions", path: "/subscriptions", icon: Repeat, roles: ["admin", "staff", "customer"] },
    { label: "Invoices", path: "/invoices", icon: Receipt, roles: ["admin", "staff", "customer"] },
    { label: "Payments", path: "/payments", icon: CreditCard, roles: ["admin", "staff", "customer"] },
    { label: "Products", path: "/products", icon: Package, roles: ["admin", "staff"] },
    { label: "Quotations", path: "/quotations", icon: FileText, roles: ["admin", "staff"] },
    { label: "Discounts", path: "/discounts", icon: Percent, roles: ["admin", "staff"] },
    { label: "Reports", path: "/reports", icon: BarChart3, roles: ["admin", "staff"] },
  ];

  const visibleNavItems = navItems.filter(
    (item) => !item.roles || item.roles.includes(role || "customer")
  );

  return (
    <>
      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-950/80 backdrop-blur-sm lg:hidden"
          onClick={onCloseMobile}
        />
      )}

      {/* Sidebar container */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-800 bg-slate-950/95 backdrop-blur-md transition-transform duration-200 lg:static lg:translate-x-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Brand Header */}
        <div className="flex h-16 items-center justify-between px-6 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-400 text-white shadow-lg shadow-brand-500/25">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
                SubFlow
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                  9.0
                </span>
              </div>
              <p className="text-[10px] text-slate-400">Subscription Engine</p>
            </div>
          </div>
        </div>

        {/* User Role Card */}
        <div className="p-4 mx-3 my-3 rounded-xl border border-slate-800/80 bg-slate-900/60">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-brand-300">
                {user?.first_name ? user.first_name[0] : "U"}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-slate-200 truncate">
                  {user?.full_name || user?.email || "User"}
                </p>
                <p className="text-[10px] text-slate-400 capitalize">{user?.role || "Member"}</p>
              </div>
            </div>
            <Badge
              variant={isAdmin ? "brand" : role === "staff" ? "warning" : "success"}
              className="text-[10px] px-1.5 py-0"
            >
              {role || "user"}
            </Badge>
          </div>
        </div>

        {/* Navigation items */}
        <nav className="flex-1 space-y-1 px-3 py-2 overflow-y-auto">
          <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
            {isCustomer ? "Customer Portal" : "Platform Modules"}
          </div>

          {visibleNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentPath === item.path;

            return (
              <button
                key={item.path}
                onClick={() => {
                  onNavigate(item.path);
                  if (onCloseMobile) onCloseMobile();
                }}
                className={cn(
                  "group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-xs font-medium transition-all duration-150 text-left",
                  isActive
                    ? "bg-brand-600 text-white shadow-md shadow-brand-500/20 font-semibold"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 shrink-0 transition-transform duration-150 group-hover:scale-110",
                    isActive ? "text-white" : "text-slate-400 group-hover:text-slate-200"
                  )}
                />
                <span className="truncate">{item.label}</span>
                {isActive && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white"></span>
                )}
              </button>
            );
          })}

          {/* Admin Management Actions */}
          {isAdmin && (
            <div className="pt-4 mt-4 border-t border-slate-800/80">
              <div className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500 flex items-center justify-between">
                <span>Administration</span>
                <Shield className="w-3 h-3 text-brand-400" />
              </div>
              <button
                onClick={onOpenCreateStaff}
                className="group flex w-full items-center gap-3 rounded-lg px-3 py-2 text-xs font-medium text-slate-400 hover:bg-slate-900 hover:text-brand-300 transition"
              >
                <UserPlus className="h-4 w-4 text-brand-400" />
                <span>Create Staff Account</span>
              </button>
            </div>
          )}
        </nav>

        {/* Footer info */}
        <div className="p-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center justify-between">
          <span>Make-A-Ton 9.0</span>
          <span className="font-mono text-[10px] text-slate-600">Core Platform</span>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
