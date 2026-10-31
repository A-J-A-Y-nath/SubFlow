import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api/v1";

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Attach JWT access token to every outgoing request
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("subflow_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Intercept responses for unified error handling and auto-logout on 401
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      // Clear expired session
      localStorage.removeItem("subflow_token");
      localStorage.removeItem("subflow_user");
      // If not already on auth page, dispatch event
      if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
        window.dispatchEvent(new CustomEvent("subflow:unauthorized"));
      }
    }
    
    // Extract standardized API error payload
    const errorData = error.response?.data?.error || {
      code: "NETWORK_ERROR",
      message: error.message || "An unexpected network error occurred",
    };
    
    return Promise.reject(errorData);
  }
);

export default api;
