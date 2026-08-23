import axios from "axios";

const getBaseUrl = () => {
  if (typeof window !== "undefined") {
    // In browser: if import.meta.env or window env is set use it, otherwise empty string so /api is relative to current origin
    const envUrl = (typeof import.meta !== "undefined" && import.meta.env && (import.meta.env.VITE_BACKEND_URL || import.meta.env.REACT_APP_BACKEND_URL)) ||
      (typeof process !== "undefined" && process.env && (process.env.VITE_BACKEND_URL || process.env.REACT_APP_BACKEND_URL));
    return envUrl ? String(envUrl).replace(/\/+$/, "") : "";
  }
  return "";
};

const BASE = getBaseUrl();

export const TOKEN_KEY = "easyx_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export const api = axios.create({
  baseURL: `${BASE}/api`,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      // Token invalid/expired — clear it. Route guards handle redirect.
      clearToken();
    }
    return Promise.reject(error);
  },
);

// Normalize FastAPI error detail to a readable string.
export const apiError = (error, fallback = "Something went wrong. Please try again.") => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && !Array.isArray(detail) && detail.message) return detail.message;
  if (Array.isArray(detail) && detail.length) return detail[0]?.msg || fallback;
  return fallback;
};

export default api;
