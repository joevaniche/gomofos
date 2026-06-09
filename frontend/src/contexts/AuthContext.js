import React, { createContext, useState, useEffect, useContext, useRef } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Ensure every request from axios includes credentials (cookies) by default.
axios.defaults.withCredentials = true;

export function formatApiErrorDetail(detail) {
  if (detail == null) return 'Something went wrong. Please try again.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === 'string' ? e.msg : JSON.stringify(e))).filter(Boolean).join(' ');
  if (detail && typeof detail.msg === 'string') return detail.msg;
  return String(detail);
}

// Singleton refresh promise so concurrent 401s only fire one /auth/refresh call.
let refreshPromise = null;

// Module-level handler (set by AuthProvider) used by the interceptor on hard failure.
let onAuthLost = null;

axios.interceptors.response.use(
  (resp) => resp,
  async (error) => {
    const original = error.config || {};
    const status = error.response?.status;

    // Only auto-refresh on 401, and never for auth endpoints themselves (avoid loops).
    const url = original.url || '';
    const isAuthEndpoint = url.includes('/api/auth/login')
                        || url.includes('/api/auth/register')
                        || url.includes('/api/auth/refresh')
                        || url.includes('/api/auth/logout');

    if (status === 401 && !original.__isRetry && !isAuthEndpoint) {
      try {
        if (!refreshPromise) {
          refreshPromise = axios.post(`${API}/auth/refresh`, {}, { withCredentials: true })
            .finally(() => { refreshPromise = null; });
        }
        await refreshPromise;
        // Retry the original request once
        original.__isRetry = true;
        return axios(original);
      } catch (refreshErr) {
        // Refresh failed — session is truly dead
        if (onAuthLost) onAuthLost();
        return Promise.reject(error);
      }
    }
    return Promise.reject(error);
  }
);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const userRef = useRef(null);
  userRef.current = user;

  useEffect(() => {
    // When refresh truly fails, clear user state so ProtectedRoute redirects to /login
    onAuthLost = () => {
      if (userRef.current) setUser(false);
    };
    checkAuth();
    return () => { onAuthLost = null; };
  }, []);

  const checkAuth = async () => {
    try {
      const { data } = await axios.get(`${API}/auth/me`, { withCredentials: true });
      setUser(data);
    } catch (e) {
      setUser(false);
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const { data } = await axios.post(`${API}/auth/login`, { email, password }, { withCredentials: true });
      setUser(data);
      return { success: true, data };
    } catch (e) {
      return { success: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const register = async (email, password, username) => {
    try {
      const { data } = await axios.post(`${API}/auth/register`, { email, password, username }, { withCredentials: true });
      setUser(data);
      return { success: true, data };
    } catch (e) {
      return { success: false, error: formatApiErrorDetail(e.response?.data?.detail) || e.message };
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
      setUser(false);
    } catch (e) {
      console.error('Logout error:', e);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
