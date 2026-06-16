import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';

// State variables to prevent multiple simultaneous refresh requests
let isRefreshing = false;
let refreshPromise: Promise<unknown> | null = null;

// Extend the Axios config to include a custom flag so we don't infinite loop
interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean;
}

const createAxiosInstance = (baseURL: string) => {
  const instance = axios.create({
    baseURL,
    timeout: 10000,
    withCredentials: true,
  });

  // --- REQUEST INTERCEPTOR (Your existing CSRF logic goes here) ---
  instance.interceptors.request.use(
    (config) => {
      // Extract CSRF token from cookies
      const csrfCookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));
        
      if (csrfCookie) {
        const csrfToken = csrfCookie.substring(10);
        config.headers['X-CSRFToken'] = csrfToken;
      }
      return config;
    },
    (error) => Promise.reject(error)
  );

  // --- RESPONSE INTERCEPTOR (Auto-Refresh Logic) ---
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as CustomAxiosRequestConfig;

      // If error is 401, we haven't retried yet, and it's not the login/refresh endpoint itself
      if (
        error.response?.status === 401 &&
        originalRequest &&
        !originalRequest._retry &&
        !originalRequest.url?.includes('/login/') &&
        !originalRequest.url?.includes('/token-refresh/')
      ) {
        originalRequest._retry = true;

        if (!isRefreshing) {
          isRefreshing = true;
          
          // Use a raw axios call to bypass interceptors and avoid infinite loops
          refreshPromise = axios.post(
            `${API_BASE_URL}/auth-api/token-refresh/`,
            {},
            { withCredentials: true }
          ).finally(() => {
            isRefreshing = false;
            refreshPromise = null;
          });
        }

        try {
          // Wait for the token to be refreshed
          await refreshPromise;
          // Retry the original request with the new cookies
          return instance(originalRequest);
        } catch (refreshError) {
          // If the refresh token is also expired, the refresh call will fail.
          // You can optionally trigger a hard logout here or redirect to /login
          const { default: authService } = await import('./authService');
          authService.logout();
          
          if (!window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
          return Promise.reject(refreshError);
        }
      }

      return Promise.reject(error);
    }
  );

  return instance;
};

export const getMediaUrl = (path: string | null | undefined) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL}${path}`;
};

export const baseApiClient = createAxiosInstance(API_BASE_URL);
export const socialApiClient = createAxiosInstance(`${API_BASE_URL}/social-api`);
export const authApiClient = createAxiosInstance(`${API_BASE_URL}/auth-api`);
export const apiClient = createAxiosInstance(`${API_BASE_URL}/api`);
