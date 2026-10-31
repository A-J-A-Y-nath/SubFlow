import React, { useState, useEffect } from "react";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import AppLayout from "./components/layout/AppLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import ProductsPage from "./pages/ProductsPage";
import PlansPage from "./pages/PlansPage";
import SubscriptionsPage from "./pages/SubscriptionsPage";
import QuotationsPage from "./pages/QuotationsPage";
import InvoicesPage from "./pages/InvoicesPage";
import PaymentsPage from "./pages/PaymentsPage";
import DiscountsPage from "./pages/DiscountsPage";
import ReportsPage from "./pages/ReportsPage";
import LoadingSpinner from "./components/common/LoadingSpinner";

function MainApp() {
  const { isAuthenticated, loading, isCustomer } = useAuth();
  const [currentPath, setCurrentPath] = useState(() => {
    const path = window.location.pathname;
    return path && path !== "/" ? path : "/dashboard";
  });

  // Role-based route guard: Customer cannot access internal management modules
  const staffOrAdminRoutes = ["/products", "/quotations", "/discounts", "/reports"];

  // Listen to browser forward/back buttons
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      setCurrentPath(path && path !== "/" ? path : "/dashboard");
    };
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  // Guard customer navigation if attempted directly
  useEffect(() => {
    if (isCustomer && staffOrAdminRoutes.includes(currentPath)) {
      navigate("/dashboard");
    }
  }, [isCustomer, currentPath]);

  const navigate = (path) => {
    if (isCustomer && staffOrAdminRoutes.includes(path)) {
      path = "/dashboard";
    }
    setCurrentPath(path);
    window.history.pushState({}, "", path);
  };

  if (loading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-slate-950">
        <LoadingSpinner message="Connecting to SubFlow Core..." size="lg" />
      </div>
    );
  }

  // Unauthenticated routing
  if (!isAuthenticated) {
    if (currentPath === "/register") {
      return <Register onNavigate={navigate} />;
    }
    return <Login onNavigate={navigate} />;
  }

  // Page titles mapping
  const titles = isCustomer
    ? {
        "/dashboard": "My Overview",
        "/plans": "Subscription Plans",
        "/subscriptions": "My Subscriptions",
        "/invoices": "My Invoices & Statements",
        "/payments": "My Payment Receipts",
      }
    : {
        "/dashboard": "System Overview",
        "/products": "Product Catalog",
        "/plans": "Subscription Plans",
        "/subscriptions": "Active Subscriptions",
        "/quotations": "Quotations & Proposals",
        "/invoices": "Invoicing & Accounts",
        "/payments": "Payment Receipts",
        "/discounts": "Discount & Promo Rules",
        "/reports": "Analytics & Performance",
      };

  // Render authenticated page with strict customer guards
  const renderPage = () => {
    switch (currentPath) {
      case "/products":
        return isCustomer ? <Dashboard onNavigate={navigate} /> : <ProductsPage />;
      case "/plans":
        return <PlansPage />;
      case "/subscriptions":
        return <SubscriptionsPage onNavigate={navigate} />;
      case "/quotations":
        return isCustomer ? <Dashboard onNavigate={navigate} /> : <QuotationsPage />;
      case "/invoices":
        return <InvoicesPage />;
      case "/payments":
        return <PaymentsPage />;
      case "/discounts":
        return isCustomer ? <Dashboard onNavigate={navigate} /> : <DiscountsPage />;
      case "/reports":
        return isCustomer ? <Dashboard onNavigate={navigate} /> : <ReportsPage />;
      case "/dashboard":
      default:
        return <Dashboard onNavigate={navigate} />;
    }
  };

  return (
    <AppLayout
      currentPath={currentPath}
      onNavigate={navigate}
      currentTitle={titles[currentPath] || "Dashboard"}
    >
      {renderPage()}
    </AppLayout>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}
