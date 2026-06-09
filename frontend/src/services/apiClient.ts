import axios from 'axios';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const MCP_BASE_URL = import.meta.env.VITE_MCP_URL || 'http://localhost:8001';

const createAxiosInstance = (baseURL) => {
  const instance = axios.create({
    baseURL,
    timeout: 10000,
    withCredentials: true,
  });

  instance.interceptors.request.use(
    (config) => config,
    (error) => Promise.reject(error)
  );

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      
      // Prevent infinite loops if the refresh token request itself fails
      if (originalRequest.url.includes('/token-refresh/')) {
        return Promise.reject(error);
      }

      // If we already retried this request, don't try again
      if (originalRequest._retry) {
        // If current-user fails even after retry, logout to prevent loops
        if (originalRequest.url.includes('/current-user/')) {
          const { default: authService } = await import('./authService');
          authService.logout();
        }
        return Promise.reject(error);
      }

      if (error.response && (error.response.status === 401 || error.response.status === 403)) {
        originalRequest._retry = true;
        try {
          const { default: authService } = await import('./authService');
          await authService.refreshToken();
          return instance(originalRequest);
        } catch (refreshError) {
          // Refresh failed - clean up and redirect
          const { default: authService } = await import('./authService');
          authService.logout();
          
          // Only redirect to login if we weren't already going there
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

export const getMediaUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL}${path}`;
};

export const baseApiClient = createAxiosInstance(API_BASE_URL);
export const socialApiClient = createAxiosInstance(`${API_BASE_URL}/social-api`);
export const authApiClient = createAxiosInstance(`${API_BASE_URL}/auth-api`);
export const apiClient = createAxiosInstance(`${API_BASE_URL}/api`);
