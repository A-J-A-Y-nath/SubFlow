import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("subflow_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => localStorage.getItem("subflow_token") || null);
  const [loading, setLoading] = useState(true);

  // Synchronize authentication on initial mount
  useEffect(() => {
    async function hydrateUser() {
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const res = await authService.getMe();
        if (res.success && res.data) {
          setUser(res.data);
          localStorage.setItem("subflow_user", JSON.stringify(res.data));
        }
      } catch {
        // Token is expired or invalid
        localStorage.removeItem("subflow_token");
        localStorage.removeItem("subflow_user");
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }

    hydrateUser();

    // Listen for unauthorized events from axios interceptor
    const handleUnauthorized = () => {
      setToken(null);
      setUser(null);
    };

    window.addEventListener("subflow:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("subflow:unauthorized", handleUnauthorized);
  }, [token]);

  const login = useCallback(async (email, password) => {
    const res = await authService.login(email, password);
    if (res.success && res.data) {
      const { user: userData, access_token } = res.data;
      localStorage.setItem("subflow_token", access_token);
      localStorage.setItem("subflow_user", JSON.stringify(userData));
      setToken(access_token);
      setUser(userData);
      return userData;
    }
    throw new Error(res.message || "Login failed");
  }, []);

  const register = useCallback(async (formData) => {
    const res = await authService.register(formData);
    if (res.success && res.data) {
      const { user: userData, access_token } = res.data;
      localStorage.setItem("subflow_token", access_token);
      localStorage.setItem("subflow_user", JSON.stringify(userData));
      setToken(access_token);
      setUser(userData);
      return userData;
    }
    throw new Error(res.message || "Registration failed");
  }, []);

  const createStaff = useCallback(async (formData) => {
    const res = await authService.createStaff(formData);
    if (res.success) {
      return res.data;
    }
    throw new Error(res.message || "Staff creation failed");
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("subflow_token");
    localStorage.removeItem("subflow_user");
    setToken(null);
    setUser(null);
  }, []);

  const value = {
    user,
    token,
    role: user?.role || null,
    isAdmin: user?.role === "admin",
    isStaff: user?.role === "staff",
    isCustomer: user?.role === "customer",
    isAuthenticated: !!token && !!user,
    loading,
    login,
    register,
    createStaff,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
