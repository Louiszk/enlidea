import axios from 'axios';
import { authApiClient } from './apiClient';
import { Account } from '../api/generated/api';

let isRefreshing = false;
let refreshPromise: Promise<unknown> | null = null;

const authService = {
  login: async (email: string, password: string) => {
    try {
      const response = await authApiClient.post('/login/', { email, password });
      return { user: response.data.user };
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.error || 'Login failed');
      }
      throw new Error('Login failed');
    }
  },

  logout: async () => {
    try {
      await authApiClient.post('/logout/');
    } catch (error) {
      console.error('Logout failed', error);
    }
    isRefreshing = false;
    refreshPromise = null;
  },

  refreshToken: async () => {
    if (isRefreshing) {
      return refreshPromise;
    }

    isRefreshing = true;
    refreshPromise = (async () => {
      try {
        const response = await authApiClient.post('/token-refresh/');
        return response.data;
      } catch (_error) {
        throw new Error('Failed to refresh token');
      } finally {
        isRefreshing = false;
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  },

  getCurrentUser: async (retry: boolean = true): Promise<Account> => {
    try {
      const response = await authApiClient.get('/current-user/');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response && error.response.status === 401 && retry) {
        try {
          await authService.refreshToken();
          return authService.getCurrentUser(false);
        } catch (_refreshError) {
          throw new Error('Session expired');
        }
      }
      if (axios.isAxiosError(error)) {
        const data = error.response?.data;
        throw new Error(data?.detail || data?.error || 'Failed to get current user');
      }
      throw new Error('Failed to get current user');
    }
  },

  activateAccount: async (uidb64: string, token: string) => {
    try {
      const response = await authApiClient.get(`/activate/${uidb64}/${token}/`);
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.error || 'Activation failed');
      }
      throw new Error('Activation failed');
    }
  },
};

export const requestPasswordReset = async (email: string) => {
  try {
    const response = await authApiClient.post('/password-reset/', { email });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 429) {
      throw new Error('Please wait 10 minutes before requesting another reset.');
    }
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'An error occurred while requesting password reset.');
    }
    throw new Error('An error occurred while requesting password reset.');
  }
};

export const confirmPasswordReset = async (uidb64: string, token: string, new_password1: string, new_password2: string) => {
  try {
    const response = await authApiClient.post(`/password-reset-confirm/${uidb64}/${token}/`, {
      new_password1,
      new_password2,
    });
    return response.data;
  } catch (error) {
    const errorData = axios.isAxiosError(error) ? error.response?.data : null;
    throw new Error(errorData?.error || errorData?.new_password1 || 'An error occurred while resetting the password.');
  }
};

export interface RegisterPayload {
  email: string;
  username: string;
  password?: string;
  [key: string]: string | undefined;
}

export const register = async (userData: RegisterPayload) => {
  try {
    const response = await authApiClient.post('/register/', userData);
    return response.data;
  } catch (error) {
    const data = axios.isAxiosError(error) ? error.response?.data : null;
    if (typeof data === 'object' && data !== null) {
      const errorMessages = Object.entries(data)
        .map(([field, errors]) => `${field}: ${Array.isArray(errors) ? errors.join(', ') : errors}`)
        .join('; ');
      throw new Error(errorMessages);
    }
    throw new Error(data?.error || 'Registration failed');
  }
};

export const checkUsernameAvailability = async (username: string) => {
  try {
    const response = await authApiClient.get(`/check-username/?username=${encodeURIComponent(username)}`);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response && error.response.status === 429) {
      throw new Error('Rate limit reached. Please wait a moment.');
    }
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'Failed to check username availability');
    }
    throw new Error('Failed to check username availability');
  }
};

export const resendActivationEmail = async (email: string) => {
  try {
    const response = await authApiClient.post('/resend-activation/', { email });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.error || 'Failed to resend activation email');
    }
    throw new Error('Failed to resend activation email');
  }
};

export default authService;
